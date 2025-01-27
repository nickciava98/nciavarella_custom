import logging
import ftplib
import socket
import os

from datetime import timedelta

from odoo import models, fields
from odoo.service import db


_logger = logging.getLogger(__name__)


class DbBackup(models.Model):
    _inherit = "db.backup"

    def _compute_name(self):
        to_compute_ids = self.filtered(lambda r: r.method == "local")

        for record in self.filtered(lambda r: r.method == "sftp"):
            record.name = (
                f"ftps://{record.sftp_user}@{record.sftp_host}:{record.sftp_port}/{record.folder}".replace("//", "/")
            )

        return super(DbBackup, to_compute_ids)._compute_name()

    def _backup_local(self):
        backup = None
        successful_ids = self.browse()

        for record in self.filtered(lambda r: r.method == "local"):
            filename = record.filename(datetime.now(), ext=record.backup_format)

            with record.backup_log():
                try:
                    os.makedirs(record.folder, exist_ok=True)

                except OSError as e:
                    _logger.exception(f"Action backup - OSError:\n{e}")

                with open(os.path.join(record.folder, filename), "wb") as destiny:
                    if backup:
                        with open(backup) as cached:
                            shutil.copyfileobj(cached, destiny)

                    else:
                        db.dump_db(self.env.cr.dbname, destiny, backup_format=record.backup_format)

                        backup = backup or destiny.name

                successful_ids |= record

        return successful_ids

    def _backup_sftp(self):
        successful_ids = self.browse()

        for record in self.filtered(lambda r: r.method == "sftp"):
            filename = record.filename(fields.Datetime.now(), ext=record.backup_format)

            with record.backup_log():
                cached = db.dump_db(
                    self.env.cr.dbname, None, backup_format=record.backup_format
                )

                with cached:
                    with record.sftp_connection() as remote:
                        try:
                            remote.mkd(record.folder)

                        except Exception as e:
                            _logger.exception(f"pysftp ConnectionException: {e}")

                        remote.storbinary(f"STOR {os.path.join(record.folder, filename)}", cached)

                    successful_ids |= record

        return successful_ids

    def action_backup(self):
        successful = self._backup_local() + self._backup_sftp()
        successful.cleanup()

    def cleanup(self):
        to_cleanup_ids = self.filtered(lambda r: r.method == "local")
        now = fields.Datetime.now()

        for record in self.filtered(lambda r: r.days_to_keep and r.method == "sftp"):
            with record.cleanup_log():
                bu_format = record.backup_format
                file_extension = bu_format == "zip" and "dump.zip" or bu_format
                oldest = self.filename(now - timedelta(days=record.days_to_keep), bu_format)

                with record.sftp_connection() as remote:
                    for name in remote.nlst(record.folder):
                        if name.endswith(".%s" % file_extension) and os.path.basename(name) < oldest:
                            remote.rmd(f"{record.folder}/{name}")

        return super(DbBackup, to_cleanup_ids).cleanup()

    def sftp_connection(self):
        self.ensure_one()

        ftps = ftplib.FTP_TLS()
        ftps.connect(self.sftp_host, self.sftp_port)
        ftps.login(self.sftp_user, self.sftp_password)
        ftps.prot_p()
        ftps.af = socket.AF_INET6

        return ftps
