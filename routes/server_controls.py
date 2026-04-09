# OpenModuli - Open Source, Self-Hosted Form Builder and Management System.
# Copyright (C) 2025 Samuele Gallicani
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from flask import Blueprint, jsonify
from utilities.server_manager import reboot_system, shutdown_system

server_bp = Blueprint('server', __name__, url_prefix='/server')

@server_bp.route("/status")
def status():
    return jsonify({"status": "ok"})

@server_bp.route("/restart")
def restart():
    reboot_system()
    return jsonify({"status": "restarting"})

@server_bp.route("/shutdown")
def shutdown():
    shutdown_system()
    return jsonify({"status": "shutting down"})