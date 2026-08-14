# Admin panel routes (Member 5).
# Everything here is read/moderate only - it reuses the same database
# functions Member 2 already wrote in database.py. No new tables, no new
# queries invented here; just wiring the existing functions to pages.

from flask import Blueprint, render_template, redirect, url_for, flash, session
from database import (
    get_admin_stats,
    get_all_users,
    get_all_requests,
    update_request_status,
    delete_request,
)
from authentication import login_required, role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# Main admin dashboard: stats + pending requests that need a decision.
@admin_bp.route("/")
@login_required
@role_required("admin")
def dashboard():

    stats = get_admin_stats()

    # status=None -> get_all_requests() returns every request regardless of status
    all_requests = get_all_requests(status=None)

    pending_requests = [r for r in all_requests if r["status"] == "pending"]

    users = get_all_users()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        all_requests=all_requests,
        pending_requests=pending_requests,
        users=users,
    )


# Approve / reject / reset a request's status.
@admin_bp.route("/requests/<int:request_id>/<status>", methods=["POST"])
@login_required
@role_required("admin")
def change_status(request_id, status):

    if status not in ("approved", "rejected", "pending"):
        flash("Invalid status.", "danger")
        return redirect(url_for("admin.dashboard"))

    updated = update_request_status(request_id, status)

    if updated:
        flash(f"Request status updated to '{status}'.", "success")
    else:
        flash("Could not update that request.", "danger")

    return redirect(url_for("admin.dashboard"))


# Admin-level delete - bypasses the "must be the owner" check with
# admin_override=True (already supported by database.delete_request).
@admin_bp.route("/requests/<int:request_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_request_admin(request_id):

    admin_id = session["user_id"]

    deleted = delete_request(request_id, admin_id, admin_override=True)

    if deleted:
        flash("Request deleted.", "success")
    else:
        flash("Could not delete that request.", "danger")

    return redirect(url_for("admin.dashboard"))
