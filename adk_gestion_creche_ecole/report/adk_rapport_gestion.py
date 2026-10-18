# -*- coding: utf-8 -*-
from odoo import api, models


class ReportAdkRapportGestion(models.AbstractModel):
    _name = 'report.adk_gestion_creche_ecole.report_rapport_gestion_document'
    _description = "Rapports de gestion scolaire (PDF)"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['adk.wizard.rapport'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'adk.wizard.rapport',
            'docs': docs,
            'rapports': {doc.id: doc._build_data() for doc in docs},
        }
