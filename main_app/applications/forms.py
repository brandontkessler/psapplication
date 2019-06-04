from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SubmitField, DateField, RadioField
from wtforms.validators import DataRequired, ValidationError

class PreConcertForm(FlaskForm):
    series_name = StringField('Name of series (used to name output)',
        validators=[DataRequired()])
    concert_date = DateField('Date of Concert (m/d/yyyy) example: 9/15/2020',
        validators=[DataRequired()], format='%m/%d/%Y')
    concert_type = RadioField('Concert type',
        choices=[('clx', 'classics'), ('pop', 'pops')])
    this_fy_toDate = FileField('This FY to date: Updated ticket report for the \
        given series',
        validators=[FileAllowed(['csv'])])
    last_year = FileField('Last FY: Updated ticket report for the \
        given series',
        validators=[FileAllowed(['csv'])])
    two_years_back = FileField('Two years back FY: Updated ticket report for \
        the given series',
        validators=[FileAllowed(['csv'])])
    three_years_back = FileField('Three years back FY: Updated ticket report\
        for the given series',
        validators=[FileAllowed(['csv'])])
    customer_info = FileField('Customer Info - (User Defined Format from a \
        List - report in Tessitura)',
        validators=[FileAllowed(['csv'])])
    donor_info = FileField('Donor Info - from the enhanced activity fund report \
        (pull 5 years of data from fiscal years)',
        validators=[FileAllowed(['csv'])])
    submit = SubmitField('Generate')

    def validate_concert_type(self, concert_type):
        if concert_type.data == "None":
            raise ValidationError('Please make a selection')
