from flask import Blueprint, render_template, flash, send_file
from flask_login import login_required
from main_app.applications.forms import PreConcertForm
from main_app.applications.util.preconcert import pre_concert_fun


applications = Blueprint('applications', __name__)


@applications.route("/preconcert", methods=["GET", "POST"])
@login_required
def preconcert():
    form = PreConcertForm()
    if form.validate_on_submit():
        name = form.series_name.data
        concert_dt = form.concert_date.data
        concert_type = form.concert_type.data
        tix1 = form.this_fy_toDate.data
        tix2 = form.last_year.data
        tix3 = form.two_years_back.data
        tix4 = form.three_years_back.data
        customer = form.customer_info.data
        donor = form.donor_info.data
        send_to_user = pre_concert_fun(name,
                                        concert_dt,
                                        concert_type,
                                        tix1,
                                        tix2,
                                        tix3,
                                        tix4,
                                        customer,
                                        donor)
        # Send file
        return send_to_user
    return render_template('preconcert.html', title='Pre Concert', form=form)
