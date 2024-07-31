import ast
import markupsafe
import json

from odoo.http import request
from odoo.addons.onlyoffice_odoo.controllers.controllers import Onlyoffice_Connector


class OnlyOfficeConnectorInherit(Onlyoffice_Connector):
    def prepare_editor_values(self, attachment, access_token, can_write):
        values = super().prepare_editor_values(attachment, access_token, can_write)
        root_config = ast.literal_eval(values.get("editorConfig"))
        editor_config = root_config.get("editorConfig")
        user = editor_config.get("user")
        user["name"] = request.env.user.name.replace("'", "")
        editor_config["user"] = user
        root_config["editorConfig"] = editor_config
        values["editorConfig"] = markupsafe.Markup(json.dumps(root_config))

        return values
