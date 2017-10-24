from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Headset, Experience, User

#for google login
from flask import session as login_session
import random, string

#gconnect
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)


CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Immersive Tech Application"


engine = create_engine('sqlite:///immersivecatalog.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route('/')
@app.route('/home')
def catalogHome():
    headset = session.query(Headset)
    experience = session.query(Experience)
    return render_template('home.html', headset = headset, experience = experience)

@app.route('/login')
def loginPage():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32)) 
    login_session['state'] = state
    return render_template('login.html', STATE = state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

    # User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
        'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id

def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user

def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


    # DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/new', methods=['GET', 'POST'])
def newEntry():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newVRHeadset = VRHeadset(
            name=request.form['name'], user_id=login_session['user_id'])
        session.add(newVRHeadset)
        flash('New VRHeadset %s Successfully Created' % newVRHeadset.name)
        session.commit()
        return redirect('/home')
    else:
        print(login_session['user_id'])
        return render_template('new.html')

@app.route('/headset/<string:headset_type>/<int:headset_id>/edit', methods=['GET', 'POST'])
def editHeadset(headset_type, headset_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedHeadset = session.query(Headset).filter_by(id=headset_id).one()
    if request.method == 'POST':
        if request.form['type']:
            editedHeadset.type = request.form['type']
        if request.form['name']:
            editedHeadset.name = request.form['name']
        if request.form['price']:
            editedHeadset.price = request.form['price']
        if request.form['FOV']:
            editedHeadset.FOV = request.form['FOV']
        if request.form['additional_components']:
            editedHeadset.additional_componenets = request.form['additional_components']
        session.add(editedHeadset)
        session.commit()
        flash('Headset Edited Yo')
        return redirect(url_for('catalogHome'))

    else:
        return render_template('edit-headset.html', headset = editedHeadset)

@app.route('/experience/<int:experience_id>/edit', methods=['GET', 'POST'])
def editExperience(experience_id):
    if 'username' not in login_session:
        return redirect('/login')
    headset = session.query(Headset)
    editedExperience = session.query(Experience).filter_by(id=experience_id).one()
    if request.form['name']:
        editedExperience.name = request.form['name']
    if request.form['description']:
        editedExperience.description = request.form['description']
    if request.form['price']:
        editedExperience.price = request.form['price']

    else:
        return render_template('edit-experience.html', headset=headset, experience=editedExperience)

@app.route('/vr/new/')
def vrEntryNew():
    return render_template('vr-new.html')

@app.route('/vr/edit/')
def vrEntryEdit():
    return render_template('edit-headset.html')

@app.route('/vr/delete/')
def vrEntryDelete():
    return render_template('vr-delete.html')

@app.route('/ar')
def arHome():
    return render_template('ar.html')

@app.route('/ar/new/')
def arEntryNew():
    return render_template('ar-new.html')

@app.route('/ar/edit/')
def arEntryEdit():
    return render_template('ar-edit.html')

@app.route('/ar/delete/')
def arEntryDelete():
    return render_template('ar-edit.html')



if __name__ == '__main__':
    app.secret_key = 'HrGlNQUEoCS_6If9--O4__N1'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)