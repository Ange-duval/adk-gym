# -*- coding: utf-8 -*-
{
    'name': 'ADK Gym Management',
    'version': '18.0.1.3.0',
    'category': 'Services/Fitness',
    'summary': 'Gestion complète de salle de sport : membres, abonnements et factures, coachs, programmes, multi-salles, inventaire, boutique et tableau de bord',
    'description': """
Module ADK GYM - Gestion complète de salle de sport pour Odoo 18
================================================================
- Gestion des membres (photo stable, IMC calculé, objectifs sportifs multiples)
- Gestion des coachs avec portefeuille membres
- Abonnements avec workflow automatisé et vue Kanban
- Programmes d'entraînement personnalisés (multi-membres, multi-coachs, multi-objectifs)
- Inventaire d'équipements partagé entre salles : un article n'est jamais dupliqué,
  chaque salle garde sa propre quantité et son propre état
- Boutique intégrée et facturation (account.move)
- Tableau de bord analytique (KPIs en temps réel)
- Documents imprimables en PDF (QWeb) : fiche membre, fiche salle, fiche coach,
  contrat d'abonnement, pass/badge membre et coach, rapport périodique d'abonnements
- Impression directe depuis les boutons "Imprimer" des fiches, ou via le menu
  Imprimer (⚙️) et l'assistant "Rapport Périodique" (menu Rapports)
""",
    'author': 'ANGE DUVAL KAMBEU',
    'maintainer': 'Kambeu Henang Ange Duval',
    'support': 'duvalkambeu61@gmail.com',
    'license': 'OPL-1',
    'price': 25.0,
    'currency': 'USD',
    'depends': [
        'base',
        'mail',
        'account',
        'product',
        'hr',
    ],
    'data': [
        # 1. Sécurité
        'security/security.xml',
        'security/ir.model.access.csv',

        # 2. Séquences et données
        'data/ir_sequence_data.xml',
        'data/gym_data.xml',
        'data/product_data.xml',
        'data/cron_data.xml',

        # 3. Rapports (actions + templates QWeb)
        'report/report_gym_templates.xml',
        'report/member_registration_template.xml',
        'report/report_coach_fiche.xml',
        'report/report_pass_templates.xml',
        'report/report_subscription.xml',

        # 4. Vues métiers (actions + kanban/list/form/search)
        'views/gym_member_views.xml',
        'views/gym_subscription_views.xml',
        'views/gym_views.xml',

        # 5. Wizards
        'wizard/gym_report_wizard_view.xml',
        'wizard/gym_subscription_renew_view.xml',

        # 6. Menus (doit être chargé en dernier : référence toutes les actions ci-dessus)
        'views/gym_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'adk_gym/static/src/js/gym_dashboard_autorefresh.js',
            'adk_gym/static/src/xml/gym_dashboard_autorefresh.xml',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/banner.png', 'static/description/icon.png'],
}
