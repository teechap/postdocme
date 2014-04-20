import base64
import uuid
from flask import (Flask, 
				  request, 
				  render_template, 
				  redirect, 
				  make_response, 
				  url_for, 
				  abort,
				  jsonify,
				  g)
import rethinkdb as r
from rethinkdb.errors import RqlRuntimeError, RqlDriverError
from boto.s3.connection import S3Connection
from boto.s3.key import Key


app = Flask(__name__, instance_relative_config=True)
app.config.from_object('config') #goes in version control
app.config.from_pyfile('config.py') #production config secretz

#=========================helper functions=====================================
def allowed_file(filename):
	return ('.' in filename) and (filename.rsplit('.', 1)[1] in \
		set(['pdf', 'PDF']))

def make_id(): #returns unique str for new document's url
	return base64.urlsafe_b64encode(uuid.uuid4().bytes).strip("=")

def upload_to_riakCS(flask_file, unique_id):
	'''
	Uploads files to Riak CS cluster. 

	param flask_file: a file obj from flask.request.files['file']
	param unique_id: a url safe uuid from make_id()
	'''
	
	conn = S3Connection(app.config['RIAKCS_ACCESS_KEY'],
						app.config['RIAKCS_SECRET_KEY'])
	bucket = conn.get_bucket(app.config['RIAKCS_BUCKET_NAME'])
	k = Key(bucket)
	k.key = unique_id + '.pdf'
	k.set_contents_from_string(flask_file.read())

#===============db setup / closing before/after requests=======================
@app.before_request
def setup_database():
	try:
		g.db_conn = r.connect(host=app.config['DBHOST'],
							  port=app.config['DBPORT'],
							  db=app.config['DBNAME'])
	except RqlDriverError:
		abort(503, "Looks like the database is down. My bad!")

@app.teardown_request
def disconnect_db():
	try:
		g.db_conn.close()
	except AttributeError:
		pass
#==============================================================================

#============================views=============================================

@app.route('/', methods=["GET", "POST"])
def index():
	if request.method == "GET":
		return render_template('index.html')
	if request.method == "POST":
		file_to_upload = request.files['file']
		fn = file_to_upload.filename
		if allowed_file(fn):
			#save metadata to rethinkdb
			unique_id = make_id()
			file_size = file_to_upload.content_length #bytes int
			db_result = r.table("pdfs").insert({
												"id": unique_id,
												"filename": fn,
												"size": file_size,
												"upload_date": r.now()
												}).run(g.db_conn)
			if db_result['errors'] == 0:
				try:
					upload_to_riakCS(file_to_upload, unique_id)
				except Exception:
					abort(500, "Server failed to upload. Ugh.")
			else:
				abort(500, "Server failed. Ugh.")
			return jsonify({'docid': unique_id}) #docid is a string
		else: #TODO? flash alert, but client side checks this anyway
			return redirect(url_for('index')) 
		
@app.route('/doc/<id>')
def get_pdf(id=None):
	if id is not None:
		#return doc from Riak CS cluster
		fn = query.name #filename
		response = make_response(doc) #doc is binary pdf string
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
	#make a list of docid strings
	#save collection list in rethinkdb (use joins or something)
	return jsonify({'colid': colid}) #str with a unique id 4 collection

@app.route('/c/<id>')
def show_collection(id=None):
	if id is not None:
		#try query collection in rethinkdb
		#make a doclist from each result in query
		#doclist is a list of dicts with docid, name, filesize keys
		doclist = [{'docid': str(doc.id), 
					'name': doc.name, 
					'size': doc.file_size} for doc in query]
		return render_template('collection.html', 
								doclist={'doclist': doclist})
	return redirect(url_for('index'))
#==============================================================================
@app.errorhandler(404)
def page_not_found(error):
	return "Crap! I can't find that page @_@", 404

if __name__ == "__main__":
	app.run(host='127.0.0.1', port=8080)
