from flask import Flask , render_template,request,redirect,url_for,session

app=Flask(__name__)
app.config['SECRET_KEY']="HelpingHands_Secret_Key_Nti"

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/login',methods=['GET','POST'])
def login():
    # <-- IF USER SUBMIT: Form Data Sent to Server -->
     if request.method == 'POST':
        return redirect(url_for('home'))

     # <-- IF USER READ ONLY: Display Login Page (GET) -->
     return render_template('login.html')
  
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/requests')
def view_requests():
    return render_template('requests.html')

@app.route('/create-request', methods=['GET', 'POST'])
def create_request():
    if request.method == 'POST':
        return redirect(url_for('view_requests'))
    return render_template('create_request.html')

@app.route('/category-cases')
def category_cases():
    return render_template('category_cases.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)