from flask import Blueprint, session, redirect, url_for, render_template, request, flash
from config import CLIENT_ID, CLIENT_SECRET, AUTHORITY, REDIRECT_URI, SCOPE
import logging
from models import User, db
from auth_helper import _build_auth_url, _get_token_from_code, _get_user_info
import msal 
import requests

# Initialize logger
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    return render_template('index.html')

@auth_bp.route('/login')
def login():
    return render_template('login.html')

@auth_bp.route('/azure_login')
def azure_login():
    session['state'] = 'random_state'
    auth_url = _build_auth_url()
    return redirect(auth_url)

@auth_bp.route('/auth/callback')
def authorized():
    try:
        code = request.args.get('code')
        if not code:
            return redirect(url_for('auth.index'))

        token = _get_token_from_code(code)
        user_info = _get_user_info(token)
        email = user_info.get('mail') or user_info.get('userPrincipalName')

        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                first_name=user_info.get('givenName', 'Unknown'),
                middle_name=None,
                last_name=user_info.get('surname', 'Unknown'),
                email=email,
                role='basicuser',
                status='active'
            )
            db.session.add(user)
            db.session.commit()

        if user.status.lower() != "active":
            flash("Account suspended. Please contact support.", "error")
            return redirect(url_for('auth.login'))

        session['user'] = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'role': user.role,
            'status': user.status
        }

        if user.role == 'admin':
            return redirect(url_for('admin.admin_home'))
        return redirect(url_for('user.basic_user_home'))
    except Exception as e:
        logger.error(f"Error during authentication: {str(e)}")
        flash("An error occurred while logging in.", "error")
        return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.index'))
