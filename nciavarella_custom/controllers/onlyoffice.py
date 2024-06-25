import json
import markupsafe
import re

from odoo.http import request

from odoo.addons.onlyoffice_odoo.utils import file_utils
from odoo.addons.onlyoffice_odoo.utils import jwt_utils
from odoo.addons.onlyoffice_odoo.utils import config_utils
from odoo.addons.onlyoffice_odoo.controllers.controllers import Onlyoffice_Connector
from odoo.addons.onlyoffice_odoo.controllers.controllers import _mobile_regex


class OnlyOfficeConnectorInherit(Onlyoffice_Connector):
    def prepare_editor_values(self, attachment, access_token, can_write):
        data = attachment.read(["id", "checksum", "public", "name", "access_token"])[0]
        docserver_url = config_utils.get_doc_server_public_url(request.env)
        odoo_url = config_utils.get_odoo_url(request.env)
        filename = data["name"]
        security_token = jwt_utils.encode_payload(
            request.env, {"id": request.env.user.id}, config_utils.get_internal_jwt_secret(request.env)
        )
        path_part = f"{data['id']}?oo_security_token={security_token}&access_token={access_token or ''}"
        document_type = file_utils.get_file_type(filename)
        is_mobile = bool(re.search(_mobile_regex, request.httprequest.headers.get("User-Agent"), re.IGNORECASE))
        root_config = {
            "width": "100%",
            "height": "100%",
            "type": is_mobile and "mobile" or "desktop",
            "documentType": document_type,
            "document": {
                "title": filename,
                "url": f"{odoo_url}onlyoffice/file/content/{path_part}",
                "fileType": file_utils.get_file_ext(filename),
                "key": f"{data['id']}{data['checksum']}",
                "permissions": {"edit": can_write}
            },
            "editorConfig": {
                "mode": can_write and "edit" or "view",
                "lang": request.env.user.lang,
                "user": {
                    "id": str(request.env.user.id),
                    "name": request.env.user.name.replace("'", "")
                },
                "customization": {}
            }
        }

        if can_write:
            root_config["editorConfig"]["callbackUrl"] = f"{odoo_url}onlyoffice/editor/callback/{path_part}"

        if jwt_utils.is_jwt_enabled(request.env):
            root_config["token"] = jwt_utils.encode_payload(request.env, root_config)

        return {
            "docTitle": filename,
            "docIcon": f"/onlyoffice_odoo/static/description/editor_icons/{document_type}.ico",
            "docApiJS": f"{docserver_url}web-apps/apps/api/documents/api.js",
            "editorConfig": markupsafe.Markup(json.dumps(root_config))
        }
