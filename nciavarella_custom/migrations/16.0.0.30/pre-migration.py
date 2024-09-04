def migrate(cr, version):
    cr.execute("ALTER TABLE account_analytic_line ADD COLUMN is_confirmed_temp boolean;")
    cr.execute("UPDATE account_analytic_line SET is_confirmed_temp = is_confirmed;")
