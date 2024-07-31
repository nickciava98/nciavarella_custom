import markupsafe

from odoo.addons.onlyoffice_odoo.controllers.controllers import Onlyoffice_Connector


class OnlyOfficeConnectorInherit(Onlyoffice_Connector):
    def prepare_editor_values(self, attachment, access_token, can_write):
        values = super().prepare_editor_values(attachment, access_token, can_write)
        root_editor_config = str(values.get("editorConfig")).replace("'", "")
        values["editorConfig"] = markupsafe.Markup(root_editor_config)

        return values
