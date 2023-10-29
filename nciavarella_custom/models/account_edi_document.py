from odoo.addons.account_edi.models.account_edi_document import AccountEdiDocument


def _process_documents_web_services(self, job_count=None, with_commit=True):
    return 0

def _process_documents_no_web_services(self):
    pass

AccountEdiDocument._process_documents_web_services = _process_documents_web_services
AccountEdiDocument._process_documents_no_web_services = _process_documents_no_web_services
