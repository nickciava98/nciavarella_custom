def migrate(cr, version):
    cr.execute("UPDATE account_analytic_line SET is_confirmed_temp = is_confirmed;")
    cr.execute("ALTER TABLE account_analytic_line DROP COLUMN is_confirmed_temp;")
