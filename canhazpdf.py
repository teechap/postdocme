import datetime
from flask import (Flask, 
				  request, 
				  render_template, 
				  redirect, 
				  make_response, 
				  url_for, 
				  abort,
				  jsonify)
from werkzeug import secure_filename
from flask.ext.mongoengine import MongoEngine, ValidationError
from bson import DBRef, ObjectId

app = Flask(__name__)

#set up database
app.config["MONGODB_SETTINGS"] = {'DB': 'pdfs'}
app.config['SECRET_KEY'] = "SUPERSECRETBADPASS"

db = MongoEngine(app)

#database schema
class PDF(db.Document):
	pdf = db.FileField(required=True)
	preview_img = db.FileField() #not implemented
	uploaded_at = db.DateTimeField(default=datetime.datetime.now)
	name = db.StringField()
	file_size = db.IntField() #not working in collections template

	def __str__(self):
		return self.uploaded_at

	meta = {
		'indexes':['-uploaded_at'],
		'ordering':['-uploaded_at']
	}

class Collection(db.Document):
	documents = db.ListField(db.ReferenceField(PDF))

#helper functions
def allowed_file(filename):
	return ('.' in filename) and (filename.rsplit('.', 1)[1] in \
		set(['pdf', 'PDF']))

#views
@app.route('/', methods=["GET", "POST"])
def index():
	if request.method == "GET":
		return render_template('index.html')
	if request.method == "POST":
		file_to_upload = request.files['file']
		fn = file_to_upload.filename
		if allowed_file(fn):
			doc = PDF(
				pdf=file_to_upload,
				name=str(secure_filename(fn)),
				file_size=file_to_upload.content_length)
			doc.save() #try to save, if not save database down
			unique_id = str(doc.id)
			return jsonify({'docid': unique_id})
		else: #client side code checks file type, not necessary
			return redirect(url_for('index')) 
		
@app.route('/doc/<id>')
def get_pdf(id=None):
	if id is not None:
		try:
			query = PDF.objects(id=id).first() #query MongoDB
		except ValidationError: #couldn't find doc with id in db
			abort(404)
		try:
			doc = query.pdf.read() #returns binary string for pdf
		except AttributeError:
			abort(404)
		fn = query.name #filename
		response = make_response(doc)
		response.headers['Content-Type'] = 'application/pdf'
		response.headers['Content-Disposition'] = \
			'inline; filename=%s.pdf' % fn
		return response
	return redirect(url_for('index'))

@app.route('/<id>')
def show_pdf(id=None):
	if id is not None:
		return render_template('document.html', doc_id=id)
	return redirect(url_for('index'))

@app.route('/collect', methods=["POST"])
def make_collection():
	doc_list = request.get_json()['docs']
	db_refs = []
	for doc in doc_list:
		ref = DBRef('PDF', ObjectId(str(doc)))
		db_refs.append(ref)
	collection = Collection(documents=db_refs)
	collection.save()
	colid = str(collection.id)
	print(str(collection.id))
	return jsonify({'colid': colid})

@app.route('/c/<id>')
def show_collection(id=None):
	if id is not None:
		#call db for collection.first()
		try:
			query = Collection.objects(id=id).first().documents
		except (ValidationError, AttributeError):
			abort(404)
		doclist = [] #list of dicts with docid, name, filesize keys
		for doc in query:
			docid = str(doc.id)
			fn = doc.name #filename
			size = doc.file_size
			doclist.append({'docid': docid, 
							'name': fn,
							'size': size})
		return render_template('collection.html', 
								doclist={'doclist': doclist})
	return redirect(url_for('index'))

'''
@app.route('/img/<id>')
def get_doc_preview(id=None):
	if id is not None:
		try:
			query = PDF.objects(id=id).first()
		except ValidationError:
			abort(404)
		img_binary = query.img_preview.read()
		fn = query.name
		response = make_response(img_binary)
		response.headers['Content-Type'] = 'image/png'
		response.headers['Content-Disposition'] = \
			'inline; filename=%s.png' % fn
		return response
	return redirect(url_for('index'))
'''

@app.errorhandler(404)
def page_not_found(error):
	return "Crap! I can't find that page @_@", 404

if __name__ == "__main__":
	app.run(debug=True)