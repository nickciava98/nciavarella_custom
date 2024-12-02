from odoo import models, fields, exceptions
from odoo.tools import float_repr


class AccountMoveDownPayment(models.Model):
    _name = "account.move.down.payment"
    _description = "Invoice Down Payment"

    date_from = fields.Date(
        string="Date From"
    )
    date_to = fields.Date(
        string="Date To"
    )
    down_payment = fields.Float(
        string="Down Payment"
    )
    stamp_duty = fields.Boolean(
        string="Stamp Duty"
    )

    _sql_constraints = [
        ("unique_dates", "UNIQUE(date_from, date_to)", "Date From and Date To must be unique!")
    ]

    def remove_record(self):
        def format_numbers(number):
            number_splited = str(number).split(".")

            if len(number_splited) == 1:
                return "%.02f" % number

            cents = number_splited[1]

            if len(cents) > 8:
                return "%.08f" % number

            return float_repr(number, max(2, len(cents)))

        move_ids = self.env["account.move"].search([("down_payment_id", "=", self.id)])

        if not move_ids:
            self.env.cr.execute(
                "DELETE FROM account_move_down_payment_res_config_settings_rel "
                f"WHERE account_move_down_payment_id = {self.id}"
            )
            self.env.cr.commit()
            self.unlink()
            self.env.cr.commit()

            return

        config = (
            f"{self.date_from} > {self.date_to}: {format_numbers(self.down_payment * 100).replace('.', ',')}% "
            f"({'con' if self.stamp_duty else 'senza'} Bollo)"
        )
        fatture = '\n- '.join(move_ids.mapped("name"))

        raise exceptions.ValidationError(
            f"Impossibile eliminare la configurazione {config} perché associata a:\n- {fatture}"
        )
