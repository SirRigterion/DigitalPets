import asyncio
import os
import socket
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import select, update, func

from src.core.config_app import settings
from src.core.config_log import logger
from src.db.database import db_helper
from src.db.models import BackgroundJob
from src.pet.background_tasks import process_pet_stats_decay, process_pet_auto_messages
from src.db.models import EmailQueue
from src.utils.email import EmailService


JOB_MIN_INTERVALS = {
    "pet_decay": timedelta(hours=0.5),
    "pet_auto_messages": timedelta(hours=1),
    "email_cleanup": timedelta(hours=6),
}

DEFAULT_MIN_INTERVAL = timedelta(minutes=5)


def _worker_id() -> str:
    """Уникальный идентификатор воркера для блокировок задач."""
    return f"{socket.gethostname()}:{os.getpid()}"


async def _reset_stale_locks(db) -> None:
    """Сброс задач, которые были в статусе in_progress слишком долго."""
    now = datetime.now(timezone.utc)
    stale_threshold = now - timedelta(seconds=300)
    try:
        stmt = (
            update(BackgroundJob)
            .where(BackgroundJob.status == "in_progress", BackgroundJob.locked_at <= stale_threshold)
            .values(
                status="pending", 
                locked_at=None, 
                locked_by=None,
                updated_at=func.now()
            )
        )
        await db.execute(stmt)
        await db.commit()
    except Exception as e:
        logger.error(f"Ошибка при сбросе старых блокировок: {e}")
        await db.rollback()


async def _ensure_default_jobs() -> None:
    """Проверяет наличие дефолтных задач и создает их, если они отсутствуют."""
    now = datetime.now(timezone.utc)
    async with db_helper.session_factory() as db:
        try:
            q = select(BackgroundJob).where(BackgroundJob.name == "pet_decay")
            res = await db.execute(q)
            job = res.scalars().first()
            if not job:
                job = BackgroundJob(
                    name="pet_decay",
                    status="pending",
                    is_recurring=True,
                    interval_seconds=int(settings.PET_DECAY_INTERVAL_SECONDS),
                    next_run=now,
                )
                db.add(job)

            q2 = select(BackgroundJob).where(BackgroundJob.name == "pet_auto_messages")
            res2 = await db.execute(q2)
            job2 = res2.scalars().first()
            if not job2:
                job2 = BackgroundJob(
                    name="pet_auto_messages",
                    status="pending",
                    is_recurring=True,
                    interval_seconds=int(settings.PET_ATTRACTION_INTERVAL_SECONDS),
                    next_run=now,
                )
                db.add(job2)

            await db.commit()
            logger.info("Дефолтные задачи созданы/проверены")
        except Exception as e:
            logger.error(f"Не удалось создать дефолтные задачи: {e}")
            await db.rollback()


async def _can_run_job(db, job: BackgroundJob) -> bool:
    """
    Проверка можно ли запустить задачу (не слишком ли рано).
    Защита от спама - проверяем когда задача последний раз выполнялась успешно.
    """
    try:
        min_interval = JOB_MIN_INTERVALS.get(job.name, DEFAULT_MIN_INTERVAL)
        
        q = select(BackgroundJob).where(
            BackgroundJob.name == job.name,
            BackgroundJob.status == "done",
            BackgroundJob.last_completed_at != None
        ).order_by(BackgroundJob.last_completed_at.desc()).limit(1)
        
        res = await db.execute(q)
        last_completed = res.scalars().first()
        
        if last_completed and last_completed.last_completed_at:
            time_since_last = datetime.now(timezone.utc) - last_completed.last_completed_at
            
            if time_since_last < min_interval:
                remaining = min_interval - time_since_last
                logger.debug(
                    f"Задача {job.name} слишком рано: "
                    f"прошло {time_since_last}, нужно {min_interval}. "
                    f"Ждём ещё {remaining}"
                )
                return False
        
        return True
        
    except Exception as e:
        logger.exception(f"Ошибка проверки интервала задачи {job.name}: {e}")
        return True 


async def _fetch_and_lock_job(db) -> Optional[BackgroundJob]:
    """
    Схема блокировки: выбираем первую подходящую задачу.
    """
    
    now = datetime.now(timezone.utc)
    try:
        q = (
            select(BackgroundJob)
            .where(BackgroundJob.status == "pending")
            .where((BackgroundJob.next_run == None) | (BackgroundJob.next_run <= now))
            .order_by(BackgroundJob.next_run.asc(), BackgroundJob.job_id.asc())
            .limit(10)
        )
        res = await db.execute(q)
        pending_jobs = res.scalars().all()
        
        if not pending_jobs:
            return None
        
        for job in pending_jobs:
            can_run = await _can_run_job(db, job)
            
            if can_run:
                try:
                    stmt = (
                        update(BackgroundJob)
                        .where(
                            BackgroundJob.job_id == job.job_id, 
                            BackgroundJob.status == "pending"
                        )
                        .values(
                            status="in_progress", 
                            locked_at=func.now(),
                            locked_by=_worker_id(), 
                            attempts=job.attempts + 1,
                            updated_at=func.now()
                        )
                    )
                    result = await db.execute(stmt)
                    await db.commit()

                    if getattr(result, "rowcount", None) in (0, None):
                        continue

                    q2 = select(BackgroundJob).where(BackgroundJob.job_id == job.job_id)
                    res2 = await db.execute(q2)
                    locked_job = res2.scalars().first()
                    
                    logger.info(f"Задача {job.name} (id={job.job_id}) заблокирована для выполнения")
                    return locked_job
                    
                except Exception as e:
                    logger.warning(f"Не удалось заблокировать задачу {job.job_id}: {e}")
                    await db.rollback()
                    continue
            else:
                logger.debug(f"Задача {job.name} (id={job.job_id}) отложена по интервалу")
        
        return None

    except Exception as e:
        logger.error(f"Ошибка выборки задачи: {e}")
        return None


async def _run_job(job: BackgroundJob) -> None:
    """
    Запускает выполнение задачи, обрабатывает результат и обновляет статус в БД.
    """
    logger.info(f"Выполнение задачи {job.name} (id={job.job_id})")
    now = datetime.now(timezone.utc)
    
    try:
        if job.name == "pet_decay":
            async with db_helper.session_factory() as task_db:
                await process_pet_stats_decay(task_db)
        elif job.name == "pet_auto_messages":
            async with db_helper.session_factory() as task_db:
                await process_pet_auto_messages(task_db)
        else:
            raise RuntimeError(f"Неизвестная задача {job.name}")

        async with db_helper.session_factory() as db:
            if job.is_recurring:
                next_run = now + timedelta(seconds=job.interval_seconds)
                stmt = (
                    update(BackgroundJob)
                    .where(BackgroundJob.job_id == job.job_id)
                    .values(
                        status="pending", 
                        next_run=next_run, 
                        locked_at=None, 
                        locked_by=None, 
                        last_error=None,
                        last_completed_at=func.now(),
                        updated_at=func.now()
                    )
                )
            else:
                stmt = (
                    update(BackgroundJob)
                    .where(BackgroundJob.job_id == job.job_id)
                    .values(
                        status="done", 
                        locked_at=None, 
                        locked_by=None, 
                        last_error=None,
                        last_completed_at=func.now(),
                        updated_at=func.now()
                    )
                )
            await db.execute(stmt)
            await db.commit()

        logger.info(f"Задача {job.name} (id={job.job_id}) выполнена успешно")

    except Exception as e:
        logger.exception(f"Ошибка при выполнении задачи {job.name} (id={job.job_id}): {e}")

        backoff = min(job.interval_seconds * (job.attempts or 1), 3600)
        next_run = now + timedelta(seconds=backoff)
        new_status = "pending" if (job.attempts < job.max_attempts) else "failed"
        async with db_helper.session_factory() as db:
            stmt = (
                update(BackgroundJob)
                .where(BackgroundJob.job_id == job.job_id)
                .values(
                    status=new_status, 
                    next_run=next_run, 
                    locked_at=None, 
                    locked_by=None, 
                    last_error=str(e)[:1900],
                    updated_at=func.now()
                )
            )
            await db.execute(stmt)
            await db.commit()


async def _process_email_queue_once(limit: int = 10):
    """Обработка очереди писем с защитой от спама."""
    now = datetime.now(timezone.utc)
    
    items_to_send = []
    async with db_helper.session_factory() as db:
        try:
            q = ( 
                select(EmailQueue)
                .where(EmailQueue.status == "pending")
                .where((EmailQueue.next_try == None) | (EmailQueue.next_try <= now))
                .order_by(EmailQueue.created_at.asc())
                .limit(limit)
            )
            res = await db.execute(q)
            items_to_send = res.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка выборки очереди писем: {e}")
            return

    for item in items_to_send:
        async with db_helper.session_factory() as db:
            try:
                stmt = (
                    update(EmailQueue)
                    .where(EmailQueue.email_id == item.email_id, EmailQueue.status == "pending")
                    .values(
                        status="in_progress", 
                        attempts=item.attempts + 1,
                        updated_at=func.now()
                    )
                )
                r = await db.execute(stmt)
                await db.commit()
                if getattr(r, "rowcount", None) in (0, None):
                    continue
            except Exception as e:
                logger.error(f"Ошибка блокировки письма {item.email_id}: {e}")
                continue

        send_error = None
        try:
            await EmailService.send_email(item.recipient, item.subject, item.body, item.is_html)
        except Exception as e:
            send_error = e

        async with db_helper.session_factory() as db:
            try:
                if not send_error:
                    stmt_done = ( 
                        update(EmailQueue)
                        .where(EmailQueue.email_id == item.email_id)
                        .values(
                            status="sent", 
                            updated_at=func.now(),
                            last_error=None
                        )
                    )
                    logger.info(f"Письмо id={item.email_id} успешно отправлено")
                else:
                    backoff = min(60 * (item.attempts or 1), 3600)
                    next_try = datetime.now(timezone.utc) + timedelta(seconds=backoff)
                    new_status = "pending" if (item.attempts < item.max_attempts) else "failed"
                    stmt_done = (
                        update(EmailQueue)
                        .where(EmailQueue.email_id == item.email_id)
                        .values(
                            status=new_status, 
                            next_try=next_try, 
                            last_error=str(send_error)[:1900],
                            updated_at=func.now()
                        )
                    )
                    logger.warning(f"Ошибка отправки письма id={item.email_id}: {send_error}")
                
                await db.execute(stmt_done)
                await db.commit()
            except Exception as e:
                logger.error(f"Ошибка обновления статуса письма id={item.email_id}: {e}")
                await db.rollback()


async def main() -> None:
    """
    Главная функция воркера.
    """
    logger.info("Запуск job worker")
    await db_helper.check_connection()
    await _ensure_default_jobs()

    CHECK_INTERVAL = 30
    EMAIL_CHECK_INTERVAL = 60

    last_email_check = datetime.now(timezone.utc)

    while True:
        try:
            now = datetime.now(timezone.utc)
            
            async with db_helper.session_factory() as db:
                await _reset_stale_locks(db)
                job = await _fetch_and_lock_job(db)
            
            time_since_email_check = (now - last_email_check).total_seconds()
            if time_since_email_check >= EMAIL_CHECK_INTERVAL:
                await _process_email_queue_once()
                last_email_check = now

            if job:
                await _run_job(job)
                await asyncio.sleep(CHECK_INTERVAL)
                continue

            await asyncio.sleep(CHECK_INTERVAL)

        except asyncio.CancelledError:
            logger.info("Job worker остановлен по сигналу")
            break
        except Exception as e:
            logger.error(f"Критическая ошибка воркера: {e}")
            await asyncio.sleep(5)
            

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Job worker завершён вручную")
