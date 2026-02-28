import ssl
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

from src.core.config_app import settings
from src.core.config_log import logger
from src.db.models import EmailQueue
from src.db.database import db_helper


class EmailService:
    """Сервис для подготовки и отправки системных уведомлений по Email."""

    staticmethod
    async def send_email(to: str, subject: str, body: str, html: bool = True) -> bool:
        """
        Отправка письма через SMTP.
        Возвращает True при успехе, False при ошибке.
        НЕ работает с БД внутри — caller сам решает, что делать при ошибке.
        """
        message = MIMEMultipart()
        message["From"] = settings.SMTP_FROM
        message["To"] = to 
        message["Subject"] = subject

        content_type = "html" if html else "plain"
        message.attach(MIMEText(body, content_type, "utf-8"))

        context = ssl.create_default_context()

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_SERVER,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_USE_SSL,
                start_tls=settings.SMTP_USE_STARTTLS,
                timeout=15, 
                tls_context=context
            )
            logger.info(f"Письмо успешно отправлено {to}")
            return True
        except Exception as e:
            logger.error(f"Не удалось отправить письмо по адресу {to}: {e}")
            return False 

    @staticmethod
    async def send_verification_email(user_email: str, user_full_name: str, token: str) -> None:
        """Отправляет письмо для подтверждения почты."""
        verify_link = f"{settings.FRONTEND_URL}/verify-email"
        ttl_seconds = settings.VERIFICATION_TTL_SECONDS
        human_ttl = (
            f"{ttl_seconds // 3600} ч." if ttl_seconds % 3600 == 0 
            else f"{ttl_seconds // 60} м."
        )
        subject = "Подтверждение почты"
        body = f"""
            <html>
            <body style="margin:0; padding:0; font-family:'Nunito', sans-serif;">
            <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td align="center" style="padding:40px 12px;">
                        <table width="480" cellpadding="0" cellspacing="0"
                            style="max-width:480px; background:#16213e; border-radius:20px;
                                    overflow:hidden; border:1px solid rgba(15,52,80,0.2);">

                            <tr>
                                <td style="padding:32px 32px 20px; text-align:center;">
                                    <h1 style="margin:0; font-size:28px; color:#ffffff;">
                                        Подтверждение <span style="color:#e94560;">почты</span>
                                    </h1>
                                    <p style="margin:16px 0 0; font-size:14px; color:#ffffff;">
                                        Здравствуйте, <span style="color:#ffffff;">{user_full_name}</span>
                                    </p>
                                </td>
                            </tr>

                            <tr>
                                <td style="padding:0 32px 32px; text-align:center;">
                                    <p style="color:#ffffff; font-size:14px; margin-bottom:20px;">
                                        Для подтверждения регистрации — нажмите кнопку ниже:
                                    </p>

                                    <a href="{verify_link}"
                                    style="display:inline-block; padding:14px 20px;
                                            background:#e94560; color:#ffffff; font-weight:700;
                                            text-decoration:none; border-radius:12px;
                                            font-size:16px;">
                                        Подтвердить почту
                                    </a>

                                    <p style="color:#ffffff; font-size:12px; margin:26px 0 12px;">
                                        Используйте данный код:
                                    </p>

                                    <div style="display:inline-block; padding:14px 18px; background:rgba(255,255,255,0.06);
                                                border:1px solid rgba(255,255,255,0.15); border-radius:12px;
                                                font-family:monospace; color:#ffffff;
                                                letter-spacing:2px; font-size:20px;">
                                        {token}
                                    </div>

                                    <p style="color:#ffffff; font-size:12px; margin-top:14px;">
                                        Действует: {human_ttl}
                                    </p>

                                    <p style="color:#ffffff; font-size:12px; margin-top:18px;">
                                        Если вы не делали этот запрос — просто проигнорируйте письмо.
                                    </p>
                                </td>
                            </tr>

                            <tr>
                                <td style="text-align:center; padding:16px;
                                        background:#111424; color:#ffffff; font-size:11px;">
                                    Это автоматическое письмо — отвечать не нужно.
                                </td>
                            </tr>

                        </table>
                    </td>
                </tr>
            </table>
            </body>
            </html>
            """
        await EmailService.send_email(user_email, subject, body)

    @staticmethod
    async def send_restore_email(user_email: str, user_full_name: str, token: str, expires_at: str) -> None:
        """Отправляет письмо для восстановления удаленного аккаунта."""
        restore_link = f"{settings.FRONTEND_URL}/user-restore"
        ttl_seconds = settings.VERIFICATION_TTL_SECONDS
        human_ttl = (
            f"{ttl_seconds // 3600} ч." if ttl_seconds % 3600 == 0 
            else f"{ttl_seconds // 60} м."
        )
        subject = "Восстановление аккаунта"
        body = f"""
            <html>
            <body style="margin:0; padding:0; font-family:'Nunito', sans-serif;">
            <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td align="center" style="padding:40px 12px;">
                        <table width="480" cellpadding="0" cellspacing="0"
                            style="max-width:480px; background:#16213e; border-radius:20px;
                                    overflow:hidden; border:1px solid rgba(15,52,80,0.2);">

                            <tr>
                                <td style="padding:32px 32px 20px; text-align:center;">
                                    <h1 style="margin:0; font-size:28px; color:#ffffff;">
                                        Восстановление <span style="color:#e94560;">аккаунта</span>
                                    </h1>
                                    <p style="margin:16px 0 0; font-size:14px; color:#ffffff;">
                                        Здравствуйте, <span style="color:#ffffff;">{user_full_name}</span>
                                    </p>
                                </td>
                            </tr>

                            <tr>
                                <td style="padding:0 32px 32px; text-align:center;">
                                    <p style="color:#ffffff; font-size:14px; margin-bottom:20px;">
                                        Ваш аккаунт помечен на удаление. Если вы хотите восстановить его — нажмите кнопку ниже:
                                    </p>

                                    <a href="{restore_link}"
                                    style="display:inline-block; padding:14px 20px;
                                            background:#e94560; color:#ffffff; font-weight:700;
                                            text-decoration:none; border-radius:12px;
                                            font-size:16px;">
                                        Восстановить аккаунт
                                    </a>

                                    <p style="color:#ffffff; font-size:12px; margin:26px 0 12px;">
                                        Используйте данный код:
                                    </p>

                                    <div style="display:inline-block; padding:14px 18px; background:rgba(255,255,255,0.06);
                                                border:1px solid rgba(255,255,255,0.15); border-radius:12px;
                                                font-family:monospace; color:#ffffff;
                                                letter-spacing:2px; font-size:20px;">
                                        {token}
                                    </div>

                                    <p style="color:#ffffff; font-size:12px; margin-top:14px;">
                                        Действует:  <strong style="color:#ffffff;">{human_ttl}</strong>
                                    </p>

                                </td>
                            </tr>

                            <tr>
                                <td style="text-align:center; padding:16px;
                                        background:#111424; color:#ffffff; font-size:11px;">
                                    Это автоматическое письмо — отвечать не нужно.
                                </td>
                            </tr>

                        </table>
                    </td>
                </tr>
            </table>
            </body>
            </html>
            """
        await EmailService.send_email(user_email, subject, body)

    @staticmethod
    async def send_reset_password_email(user_email: str, user_full_name: str, token: str, expires_at: str) -> None:
        """Отправляет инструкцию по сбросу пароля."""
        reset_link = f"{settings.FRONTEND_URL}/reset-password"
        ttl_seconds = settings.RESET_PASSWORD_TTL_SECONDS
        human_ttl = (
            f"{ttl_seconds // 3600} ч." if ttl_seconds % 3600 == 0 
            else f"{ttl_seconds // 60} м."
        )
        subject = "Сброс пароля"
        body = f"""
            <html>
            <body style="margin:0; padding:0; font-family:'Nunito', sans-serif;">
            <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td align="center" style="padding:40px 12px;">
                        <table width="480" cellpadding="0" cellspacing="0"
                            style="max-width:480px; background:#16213e; border-radius:20px;
                                    overflow:hidden; border:1px solid rgba(15,52,80,0.2);">

                            <tr>
                                <td style="padding:32px 32px 20px; text-align:center;">
                                    <h1 style="margin:0; font-size:28px; color:#ffffff;">
                                        Сброс <span style="color:#e94560;">пароля</span>
                                    </h1>
                                    <p style="margin:16px 0 0; font-size:14px; color:#ffffff;">
                                        Здравствуйте, <span style="color:#ffffff;">{user_full_name}</span>
                                    </p>
                                </td>
                            </tr>

                            <tr>
                                <td style="padding:0 32px 32px; text-align:center;">
                                    <p style="color:#ffffff; font-size:14px; margin-bottom:20px;">
                                        Чтобы установить новый пароль — нажмите кнопку ниже:
                                    </p>

                                    <a href="{reset_link}"
                                    style="display:inline-block; padding:14px 20px;
                                            background:#e94560; color:#ffffff; font-weight:700;
                                            text-decoration:none; border-radius:12px;
                                            font-size:16px;">
                                        Сбросить пароль
                                    </a>

                                    <p style="color:#ffffff; font-size:12px; margin:26px 0 12px;">
                                        Используйте данный код:
                                    </p>

                                    <div style="display:inline-block; padding:14px 18px; background:rgba(255,255,255,0.06);
                                                border:1px solid rgba(255,255,255,0.15); border-radius:12px;
                                                font-family:monospace; color:#ffffff;
                                                letter-spacing:2px; font-size:20px;">
                                        {token}
                                    </div>

                                    <p style="color:#ffffff; font-size:12px; margin-top:14px;">
                                        Действует: {human_ttl}
                                    </p>
                                </td>
                            </tr>

                            <tr>
                                <td style="text-align:center; padding:16px;
                                        background:#111424; color:#ffffff; font-size:11px;">
                                    Это автоматическое письмо — отвечать не нужно.
                                </td>
                            </tr>

                        </table>
                    </td>
                </tr>
            </table>
            </body>
            </html>
            """
    
        await EmailService.send_email(user_email, subject, body)
        
    @staticmethod
    async def send_delete_email(user_email: str, user_full_name: str) -> None:
        """Отправляет уведомление о том, что аккаунт был удалён."""
        subject = "Ваш аккаунт был удалён"
        support_link = f"{settings.FRONTEND_URL}/pet"
        body = f"""
            <html>
            <body style="margin:0; padding:0; font-family:'Nunito', sans-serif;">
            <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td align="center" style="padding:40px 12px;">
                        <table width="480" cellpadding="0" cellspacing="0"
                            style="max-width:480px; background:#16213e; border-radius:20px;
                                    overflow:hidden; border:1px solid rgba(15,52,80,0.2);">

                            <!-- HEADER -->
                            <tr>
                                <td style="padding:32px 32px 20px; text-align:center;">
                                    <h1 style="margin:0; font-size:28px; color:#ffffff;">
                                        Аккаунт <span style="color:#e94560;">удалён</span>
                                    </h1>
                                    <p style="margin:16px 0 0; font-size:14px; color:#ffffff;">
                                        Здравствуйте, <span style="color:#ffffff;">{user_full_name}</span>
                                    </p>
                                </td>
                            </tr>

                            <!-- CONTENT -->
                            <tr>
                                <td style="padding:0 32px 32px; text-align:center;">

                                    <p style="color:#ffffff; font-size:14px; margin-bottom:20px;">
                                        Ваш аккаунт был удалён без возможности самостоятельного восстановления
                                    </p>

                                    <a href="{support_link}"
                                    style="display:inline-block; padding:14px 22px;
                                            background:#e94560; color:#ffffff; font-weight:700;
                                            text-decoration:none; border-radius:12px;
                                            font-size:16px; margin-bottom:26px;">
                                        Зайти в игру
                                    </a>


                                    <p style="color:#ffffff; font-size:12px; margin-top:18px;">
                                        Если это произошло по ошибке — проигнорируйте письмо.
                                    </p>

                                </td>
                            </tr>

                            <!-- FOOTER -->
                            <tr>
                                <td style="text-align:center; padding:16px;
                                        background:#111424; color:#ffffff; font-size:11px;">
                                    Это автоматическое письмо — отвечать не нужно.
                                </td>
                            </tr>

                        </table>
                    </td>
                </tr>
            </table>
            </body>
            </html>
            """
        await EmailService.send_email(user_email, subject, body)
        
    
    @staticmethod
    async def send_bad_pet_email(user_email: str, user_full_name: str, pet_names: list[str]) -> None:
        """Отправляет уведомление о том, что питомцу(ам) плохо."""
        is_multiple = len(pet_names) > 1
        pets_formatted = ", ".join(pet_names)
        
        subject = "Вашим питомцам плохо" if is_multiple else "Вашему питомцу плохо"
        title_text = "Питомцам плохо" if is_multiple else "Питомцу плохо"
        
        message_text = (
            f"Ваши питомцы <b>{pets_formatted}</b> чувствуют себя плохо — их характеристики находятся на критически низком уровне. "
            f"Пожалуйста, зайдите в приложение и позаботьтесь о них."
            if is_multiple else
            f"Ваш питомец <b>{pets_formatted}</b> чувствует себя плохо — его характеристики находятся на критически низком уровне. "
            f"Пожалуйста, зайдите в приложение и позаботьтесь о нём."
        )

        support_link = f"{settings.FRONTEND_URL}/pet"
        body = f"""
            <html>
            <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            </head>
            <body style="margin:0; padding:0; font-family:'Nunito', sans-serif;">
            <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td align="center" style="padding:40px 12px;">
                        <table width="480" cellpadding="0" cellspacing="0"
                            style="width:100%; max-width:480px; background:#16213e; border-radius:20px;
                                    overflow:hidden; border:1px solid rgba(15,52,80,0.2);">

                            <tr>
                                <td style="padding:32px 32px 20px; text-align:center;">
                                    <h1 style="margin:0; font-size:26px; color:#ffffff; line-height:1.3;">
                                        <span style="color:#e94560;">Внимание!</span> 
                                    </h1>
                                    <h1 style="margin:0; font-size:26px; color:#ffffff; line-height:1.3;">
                                        {title_text}
                                    </h1>
                                    <p style="margin:16px 0 0; font-size:15px; color:#ffffff;">
                                        Здравствуйте, <span style="color:#ffffff;">{user_full_name}</span>
                                    </p>
                                </td>
                            </tr>

                            <tr>
                                <td style="padding:0 32px 32px; text-align:center;">

                                    <p style="color:#ffffff; font-size:15px; margin-bottom:22px; line-height:1.5;">
                                        {message_text}
                                    </p>

                                    <a href="{support_link}"
                                    style="display:inline-block; padding:14px 22px;
                                            background:#e94560; color:#ffffff; font-weight:700;
                                            text-decoration:none; border-radius:12px;
                                            font-size:16px; margin-bottom:26px;">
                                        Зайти в игру
                                    </a>

                                    <p style="color:#ffffff; font-size:12px; margin-top:18px; line-height:1.4;">
                                        Если вы считаете, что получили это сообщение по ошибке —
                                        проигнорируйте письмо.
                                    </p>

                                </td>
                            </tr>

                            <tr>
                                <td style="text-align:center; padding:16px;
                                        background:#111424; color:#ffffff; font-size:11px; line-height:1.4;">
                                    Это автоматическое письмо — отвечать не нужно.
                                </td>
                            </tr>

                        </table>
                    </td>
                </tr>
            </table>
            </body>
            </html>
            """
        await EmailService.send_email(user_email, subject, body)
        
    @staticmethod
    async def send_run_pet_email(user_email: str, user_full_name: str, pet_names: list[str]) -> None:
        """Отправляет уведомление о том, что питомец(ы) сбежал(и) или в опасности."""
        is_multiple = len(pet_names) > 1
        pets_formatted = ", ".join(pet_names)
        
        subject = "Ваши питомцы в опасности" if is_multiple else "Ваш питомец в опасности"
        title_text = "Питомцы в опасности" if is_multiple else "Питомец в опасности"
        
        message_text = (
            f"Ваши питомцы <b>{pets_formatted}</b> находятся в опасности.<br>"
            f"Их здоровье достигло 0. Если в ближайшее время не позаботиться о них, "
            f"питомцы могут сбежать и придётся их искать."
            if is_multiple else
            f"Ваш питомец <b>{pets_formatted}</b> находится в опасности.<br>"
            f"Его здоровье достигло 0. Если в ближайшее время не позаботиться о нём, "
            f"питомец может сбежать и придётся его искать."
        )

        support_link = f"{settings.FRONTEND_URL}/pet"
        body = f"""
            <html>
            <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            </head>

            <body style="margin:0; padding:0; font-family:'Nunito', sans-serif;">
            <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td align="center" style="padding:40px 12px;">
                        <table width="480" cellpadding="0" cellspacing="0"
                            style="width:100%; max-width:480px; background:#16213e; border-radius:20px;
                                    overflow:hidden; border:1px solid rgba(15,52,80,0.2);">

                            <tr>
                                <td style="padding:32px 32px 20px; text-align:center;">
                                    <h1 style="margin:0; font-size:26px; color:#ffffff; line-height:1.3;">
                                        <span style="color:#e94560;">Внимание!</span> 
                                    </h1>
                                    <h1 style="margin:0; font-size:26px; color:#ffffff; line-height:1.3;">
                                        {title_text}
                                    </h1>
                                    <p style="margin:16px 0 0; font-size:15px; color:#ffffff;">
                                        Здравствуйте, <span style="color:#ffffff;">{user_full_name}</span>
                                    </p>
                                </td>
                            </tr>

                            <tr>
                                <td style="padding:0 32px 32px; text-align:center;">

                                    <p style="color:#ffffff; font-size:15px; margin-bottom:22px; line-height:1.5;">
                                        {message_text}
                                    </p>

                                    <a href="{support_link}"
                                    style="display:inline-block; padding:14px 22px;
                                            background:#e94560; color:#ffffff; font-weight:700;
                                            text-decoration:none; border-radius:12px;
                                            font-size:16px; margin-bottom:26px;">
                                        Зайти в игру
                                    </a>

                                    <p style="color:#ffffff; font-size:12px; margin-top:18px; line-height:1.4;">
                                        Если вы считаете, что получили это сообщение по ошибке —
                                        проигнорируйте письмо.
                                    </p>

                                </td>
                            </tr>

                            <tr>
                                <td style="text-align:center; padding:16px;
                                        background:#111424; color:#ffffff; font-size:11px; line-height:1.4;">
                                    Это автоматическое письмо — отвечать не нужно.
                                </td>
                            </tr>

                        </table>
                    </td>
                </tr>
            </table>
            </body>
            </html>
            """
        await EmailService.send_email(user_email, subject, body)