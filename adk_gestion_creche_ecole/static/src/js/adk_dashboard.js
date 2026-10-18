/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const STATUT_COLORS = {
    present: "#4CAF8A",
    absent: "#E8697D",
    retard: "#F0B860",
    excuse: "#8FA6D6",
};

const STATUT_LABELS = {
    present: "Présent",
    absent: "Absent",
    retard: "En retard",
    excuse: "Justifiée",
};

export class AdkDashboard extends Component {
    static template = "adk_gestion_creche_ecole.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.state = useState({
            loading: true,
            error: null,
            today: "",
            kpis: {
                eleves: 0,
                classes: 0,
                tauxPresence: 0,
                absencesJour: 0,
                moyenneGenerale: 0,
                bulletinsBrouillon: 0,
                pretsRetard: 0,
                badgesActifs: 0,
                pointagesJour: 0,
                entreesJour: 0,
                sortiesJour: 0,
                chiffreAffaires: 0,
                chiffreAffairesMois: 0,
                encaissements: 0,
                impayes: 0,
                depenses: 0,
            },
            financeDisponible: false,
            presenceBreakdown: [],
            absencesListe: [],
            classesAbsences: [],
        });

        onWillStart(() => this.loadDashboard());
    }

    async loadDashboard() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const now = new Date();
            const toLocalDate = (date) => {
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, "0");
                const day = String(date.getDate()).padStart(2, "0");
                return `${year}-${month}-${day}`;
            };
            const todayStr = toLocalDate(now);
            const monthStart = toLocalDate(new Date(now.getFullYear(), now.getMonth(), 1));
            const nextMonthStart = toLocalDate(new Date(now.getFullYear(), now.getMonth() + 1, 1));
            this.state.today = new Intl.DateTimeFormat("fr-FR", {
                weekday: "long",
                day: "numeric",
                month: "long",
                year: "numeric",
            }).format(new Date());

            const [
                elevesCount,
                classesCount,
                bulletinsBrouillon,
                pretsRetard,
                badgesActifs,
                pointagesJour,
                entreesJour,
                sortiesJour,
                presenceToday,
                noteStats,
                absencesRecentes,
            ] = await Promise.all([
                this.orm.searchCount("adk.eleve", [["active", "=", true]]),
                this.orm.searchCount("adk.classe", [["active", "=", true]]),
                this.orm.searchCount("adk.bulletin", [["etat", "=", "brouillon"]]),
                this.orm.searchCount("adk.pret.livre", [["statut", "=", "retard"]]),
                this.orm.searchCount("adk.badge", [["statut", "=", "actif"]]),
                this.orm.searchCount("adk.pointage", [["heure_pointage", ">=", `${todayStr} 00:00:00`], ["heure_pointage", "<", `${toLocalDate(new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1))} 00:00:00`]]),
                this.orm.searchCount("adk.pointage", [["heure_pointage", ">=", `${todayStr} 00:00:00`], ["heure_pointage", "<", `${toLocalDate(new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1))} 00:00:00`], ["type_mouvement", "=", "entree"]]),
                this.orm.searchCount("adk.pointage", [["heure_pointage", ">=", `${todayStr} 00:00:00`], ["heure_pointage", "<", `${toLocalDate(new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1))} 00:00:00`], ["type_mouvement", "=", "sortie"]]),
                this.orm.readGroup(
                    "adk.presence",
                    [["date", "=", todayStr]],
                    ["statut"],
                    ["statut"],
                    { lazy: false }
                ),
                this.orm.readGroup(
                    "adk.note",
                    [],
                    ["note_ponderee_20:avg"],
                    []
                ),
                this.orm.searchRead(
                    "adk.presence",
                    [["date", "=", todayStr], ["statut", "=", "absent"]],
                    ["eleve_id", "classe_id", "motif"],
                    { limit: 8, order: "id desc" }
                ),
            ]);

            this.state.kpis.eleves = elevesCount;
            this.state.kpis.classes = classesCount;
            this.state.kpis.bulletinsBrouillon = bulletinsBrouillon;
            this.state.kpis.pretsRetard = pretsRetard;
            this.state.kpis.badgesActifs = badgesActifs;
            this.state.kpis.pointagesJour = pointagesJour;
            this.state.kpis.entreesJour = entreesJour;
            this.state.kpis.sortiesJour = sortiesJour;
            this.state.kpis.moyenneGenerale = noteStats.length
                ? (noteStats[0].note_ponderee_20 || 0)
                : 0;

            // Les indicateurs financiers respectent les droits comptables de l'utilisateur.
            // Leur indisponibilité ne doit pas bloquer le reste du tableau de bord.
            try {
                const Move = "account.move";
                const aggregate = async (domain) => {
                    const rows = await this.orm.readGroup(
                        Move,
                        domain,
                        ["amount_total:sum", "amount_residual:sum"],
                        []
                    );
                    const row = rows && rows.length ? rows[0] : {};
                    return {
                        total: Number(row.amount_total ?? row.amount_total_sum ?? 0),
                        residual: Number(row.amount_residual ?? row.amount_residual_sum ?? 0),
                    };
                };
                const postedCustomerInvoices = [["move_type", "=", "out_invoice"], ["state", "=", "posted"]];
                const postedVendorBills = [["move_type", "=", "in_invoice"], ["state", "=", "posted"]];
                const [allSales, monthlySales, vendorBills] = await Promise.all([
                    aggregate(postedCustomerInvoices),
                    aggregate([...postedCustomerInvoices, ["invoice_date", ">=", monthStart], ["invoice_date", "<", nextMonthStart]]),
                    aggregate(postedVendorBills),
                ]);
                this.state.kpis.chiffreAffaires = allSales.total;
                this.state.kpis.chiffreAffairesMois = monthlySales.total;
                this.state.kpis.encaissements = Math.max(0, allSales.total - allSales.residual);
                this.state.kpis.impayes = Math.max(0, allSales.residual);
                this.state.kpis.depenses = vendorBills.total;
                this.state.financeDisponible = true;
            } catch (financeError) {
                this.state.financeDisponible = false;
                console.info("Indicateurs financiers masqués : droits comptables insuffisants ou comptabilité indisponible.");
            }

            let total = 0;
            const counts = { present: 0, absent: 0, retard: 0, excuse: 0 };
            for (const group of presenceToday) {
                counts[group.statut] = group.__count || group.statut_count || 0;
                total += counts[group.statut];
            }
            this.state.kpis.absencesJour = counts.absent;
            this.state.kpis.tauxPresence = total
                ? Math.round(((counts.present + counts.retard) / total) * 100)
                : 0;

            this.state.presenceBreakdown = Object.keys(STATUT_LABELS).map((key) => ({
                key,
                label: STATUT_LABELS[key],
                color: STATUT_COLORS[key],
                value: counts[key] || 0,
                pct: total ? Math.round(((counts[key] || 0) / total) * 100) : 0,
            }));

            this.state.absencesListe = absencesRecentes.map((rec) => ({
                id: rec.id,
                eleve: rec.eleve_id ? rec.eleve_id[1] : "—",
                classe: rec.classe_id ? rec.classe_id[1] : "—",
                motif: rec.motif || "Non renseigné",
            }));

            // Taux d'absence par classe sur les 30 derniers jours
            const dateLimite = new Date();
            dateLimite.setDate(dateLimite.getDate() - 30);
            const dateLimiteStr = toLocalDate(dateLimite);

            const groupsParClasse = await this.orm.readGroup(
                "adk.presence",
                [["date", ">=", dateLimiteStr]],
                ["classe_id", "statut"],
                ["classe_id", "statut"],
                { lazy: false }
            );

            const parClasse = {};
            for (const g of groupsParClasse) {
                if (!g.classe_id) continue;
                const key = g.classe_id[1];
                if (!parClasse[key]) {
                    parClasse[key] = { name: key, total: 0, absent: 0 };
                }
                const c = g.__count || 0;
                parClasse[key].total += c;
                if (g.statut === "absent") {
                    parClasse[key].absent += c;
                }
            }
            this.state.classesAbsences = Object.values(parClasse)
                .map((c) => ({
                    name: c.name,
                    taux: c.total ? Math.round((c.absent / c.total) * 100) : 0,
                }))
                .sort((a, b) => b.taux - a.taux)
                .slice(0, 6);
        } catch (e) {
            this.state.error = "Impossible de charger certaines données du tableau de bord.";
            console.error(e);
        } finally {
            this.state.loading = false;
        }
    }

    donutStyle() {
        let acc = 0;
        const stops = [];
        for (const seg of this.state.presenceBreakdown) {
            if (!seg.pct) continue;
            const start = acc;
            const end = acc + seg.pct;
            stops.push(`${seg.color} ${start}% ${end}%`);
            acc = end;
        }
        if (!stops.length) {
            return "background: conic-gradient(#E7E9F0 0% 100%);";
        }
        return `background: conic-gradient(${stops.join(", ")});`;
    }

    refresh() {
        return this.loadDashboard();
    }

    formatMoney(value) {
        const amount = Number(value || 0);
        return `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(amount)} FCFA`;
    }

    openCustomerInvoices() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Factures clients validées",
            res_model: "account.move",
            views: [[false, "list"], [false, "form"]],
            domain: [["move_type", "=", "out_invoice"], ["state", "=", "posted"]],
        });
    }

    openVendorBills() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Factures fournisseurs validées",
            res_model: "account.move",
            views: [[false, "list"], [false, "form"]],
            domain: [["move_type", "=", "in_invoice"], ["state", "=", "posted"]],
        });
    }

    openEleves() {
        this.actionService.doAction("adk_gestion_creche_ecole.action_adk_eleve");
    }

    openClasses() {
        this.actionService.doAction("adk_gestion_creche_ecole.action_adk_classe");
    }

    openPresencesJour() {
        const todayStr = new Date().toISOString().slice(0, 10);
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Présences du jour",
            res_model: "adk.presence",
            views: [[false, "list"], [false, "form"]],
            domain: [["date", "=", todayStr]],
        });
    }

    openAbsencesJour() {
        const todayStr = new Date().toISOString().slice(0, 10);
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Absences du jour",
            res_model: "adk.presence",
            views: [[false, "list"], [false, "form"]],
            domain: [["date", "=", todayStr], ["statut", "=", "absent"]],
        });
    }

    openBulletinsBrouillon() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Bulletins en brouillon",
            res_model: "adk.bulletin",
            views: [[false, "list"], [false, "form"]],
            domain: [["etat", "=", "brouillon"]],
        });
    }

    openPretsRetard() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Prêts en retard",
            res_model: "adk.pret.livre",
            views: [[false, "list"], [false, "form"]],
            domain: [["statut", "=", "retard"]],
        });
    }

    openPointages() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Pointages — entrées et sorties du jour",
            res_model: "adk.pointage",
            views: [[false, "list"], [false, "form"]],
            domain: [["heure_pointage", ">=", `${new Date().getFullYear()}-${String(new Date().getMonth()+1).padStart(2,"0")}-${String(new Date().getDate()).padStart(2,"0")} 00:00:00`]],
            context: { search_default_group_by_type_mouvement: 1 },
        });
    }

    openBadges() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Badges actifs",
            res_model: "adk.badge",
            views: [[false, "list"], [false, "form"]],
            domain: [["statut", "=", "actif"]],
        });
    }

    openNotes() {
        this.actionService.doAction("adk_gestion_creche_ecole.action_adk_note");
    }

    openEleve(id) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "adk.presence",
            views: [[false, "form"]],
            res_id: id,
        });
    }
}

registry.category("actions").add("adk_dashboard", AdkDashboard);
