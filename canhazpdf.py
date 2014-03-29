import datetime
import os
from flask import (Flask, 
				  request, 
				  render_template, 
				  redirect, 
				  make_response, 
				  url_for, 
				  abort,
				  jsonify,
				  g)
from werkzeug import secure_filename

app = Flask(__name__)


#helper functions
def allowed_file(filename):
	return ('.' in filename) and (filename.rsplit('.', 1)[1] in \
		set(['pdf', 'PDF']))

#views
@app.route('/', methods=["GET", "POST"])
def index():
	if request.method == "GET":
		#make lots of documents and return a JSON object with ob ids
		
		return render_template('index.html')
	if request.method == "POST":
		file_to_upload = request.files['file']
		fn = file_to_upload.filename
		if allowed_file(fn):
			#save metadata to rethinkdb
			#then save file to riakCS cluster

			return jsonify({'docid': unique_id}) #docid is a string
		else: #client side code checks file type, not necessary
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

@app.errorhandler(404)
def page_not_found(error):
	return "Crap! I can't find that page @_@", 404

if __name__ == "__main__":
	app.run(host='127.0.0.1', port=8080)
