from django.urls import path

from .public_views import (
    public_catalog,
    public_panel_detail,
    public_reservation_request,
    public_reservation_success,
    private_agency_catalog,
    private_agency_panel_detail,
)
from .views import (
    geographic_units_api,
    geographic_unit_chain_api,
    dashboard,
    action_center,
    home,
    panel_create,
    panel_detail,
    panel_face_create,
    panel_face_update,
    panel_face_image_create,
    panel_face_image_update,
    panel_face_detail,
    panel_faces_by_agency_api,
    panel_list,
    panel_update,
    panel_import_upload,
    panel_import_batch_list,
    panel_import_wizard,
    panel_import_summary,
    panel_import_configure,
    panel_import_cancel,

    panel_qr_code_image,
    panel_qr_code_download_pdf,
    panel_qr_code_download_png,
    panel_qr_code_download_svg,

    reservation_change_status,
    reservation_interrupt,
    reservation_create,
    reservation_detail,
    reservation_list,
    reservation_update,

    reservation_tax_line_create,
    reservation_tax_line_update,
    reservation_tax_line_delete,

    UserListView,
    UserCreateView,
    UserToggleStatusView,
    UserUpdateView,
    UserResetPasswordTriggerView,
    SelfProfileUpdateView,

    client_list,
    client_detail,
    client_create,
    client_update,
    agency_list,
    agency_create,
    agency_update,
    agency_profile,
    reservation_invoice_pdf,
)

urlpatterns = [
    path("", home, name="home"),
    path("catalog/", public_catalog, name="public_catalog"),
    path("catalog/panels/<int:panel_id>/", public_panel_detail, name="public_panel_detail"),
    path("catalog/panels/<int:panel_id>/request/", public_reservation_request, name="public_reservation_request_for_panel"),
    path(
        "agency-catalog/<slug:agency_slug>/",
        private_agency_catalog,
        name="private_agency_catalog",
    ),
    path(
        "agency-catalog/<slug:agency_slug>/panels/<int:panel_id>/",
        private_agency_panel_detail,
        name="private_agency_panel_detail",
    ),
    path("request-reservation/", public_reservation_request, name="public_reservation_request"),
    path("request-reservation/success/", public_reservation_success, name="public_reservation_success"),
    path("dashboard/", dashboard, name="dashboard"),
    path("actions/", action_center, name="action_center"),
    path("panels/", panel_list, name="panel_list"),
    path("panels/create/", panel_create, name="panel_create"),
    path("panels/<int:panel_id>/", panel_detail, name="panel_detail"),
    path("panels/<int:panel_id>/edit/", panel_update, name="panel_update"),
    path("panels/<int:panel_id>/faces/create/", panel_face_create, name="panel_face_create"),

    path("panels/import/", panel_import_upload, name="panel_import_upload"),
    path("panels/import/batches/", panel_import_batch_list, name="panel_import_batch_list"),
    path("panels/import/<int:batch_id>/", panel_import_wizard, name="panel_import_wizard"),
    path("panels/import/<int:batch_id>/summary/", panel_import_summary, name="panel_import_summary"),
    path("panels/import/<int:batch_id>/configure/", panel_import_configure, name="panel_import_configure"),
    path("panels/import/<int:batch_id>/cancel/", panel_import_cancel, name="panel_import_cancel"),

    path("panels/<int:panel_id>/qr-code.png", panel_qr_code_image, name="panel_qr_code_image"),
    path("panels/<int:panel_id>/qr-code/download.pdf", panel_qr_code_download_pdf, name="panel_qr_code_download_pdf"),
    path("panels/<int:panel_id>/qr-code/download.png", panel_qr_code_download_png, name="panel_qr_code_download_png"),
    path("panels/<int:panel_id>/qr-code/download.svg", panel_qr_code_download_svg, name="panel_qr_code_download_svg"),

    path("faces/<int:face_id>/edit/", panel_face_update, name="panel_face_update"),
    path("faces/<int:face_id>/images/create/", panel_face_image_create, name="panel_face_image_create"),
    path("faces/<int:face_id>/", panel_face_detail, name="panel_face_detail"),
    path("face-images/<int:image_id>/edit/", panel_face_image_update, name="panel_face_image_update"),
    path("reservations/", reservation_list, name="reservation_list"),
    path("reservations/create/", reservation_create, name="reservation_create"),
    path("reservations/<int:reservation_id>/", reservation_detail, name="reservation_detail"),
    path("reservations/<int:reservation_id>/edit/", reservation_update, name="reservation_update"),
    path(
        "reservations/<int:reservation_id>/status/<str:new_status>/",
        reservation_change_status,
        name="reservation_change_status",
    ),
    path(
        "reservations/<int:reservation_id>/interrupt/",
        reservation_interrupt,
        name="reservation_interrupt",
    ),

    path(
        "reservations/<int:reservation_id>/tax-lines/create/",
        reservation_tax_line_create,
        name="reservation_tax_line_create",
    ),
    path(
        "reservations/<int:reservation_id>/tax-lines/<int:line_id>/edit/",
        reservation_tax_line_update,
        name="reservation_tax_line_update",
    ),
    path(
        "reservations/<int:reservation_id>/tax-lines/<int:line_id>/delete/",
        reservation_tax_line_delete,
        name="reservation_tax_line_delete",
    ),

    path("api/panel-faces/", panel_faces_by_agency_api, name="panel_faces_by_agency_api"),
    path("api/geographic-units/", geographic_units_api, name="geographic_units_api"),
    path("api/geographic-unit-chain/", geographic_unit_chain_api, name="geographic_unit_chain_api"),

    path("backoffice/users/", UserListView.as_view(), name="user_list"),
    path("backoffice/users/create/", UserCreateView.as_view(), name="user_create"),
    path("backoffice/users/<int:pk>/toggle/", UserToggleStatusView.as_view(), name="user_toggle_status"),
    path("backoffice/users/<int:pk>/edit/", UserUpdateView.as_view(), name="user_edit"),
    path("backoffice/users/<int:pk>/reset-password/", UserResetPasswordTriggerView.as_view(),
         name="user_reset_password_trigger"),
    path("backoffice/my-profile/", SelfProfileUpdateView.as_view(), name="my_profile"),

    path("clients/", client_list, name="client_list"),
    path("clients/create/", client_create, name="client_create"),
    path("clients/<int:client_id>/", client_detail, name="client_detail"),
    path("clients/<int:client_id>/edit/", client_update, name="client_update"),

    path("agencies/", agency_list, name="agency_list"),
    path("agencies/create/", agency_create, name="agency_create"),
    path("agencies/<int:agency_id>/edit/", agency_update, name="agency_update"),
    path("agency-profile/", agency_profile, name="agency_profile"),

    path(
        "reservations/<int:reservation_id>/invoice/",
        reservation_invoice_pdf,
        name="reservation_invoice_pdf",
    ),


]