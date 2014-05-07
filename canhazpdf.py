import base64
import uuid
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
import rethinkdb as r
from rethinkdb.errors import RqlRuntimeError, RqlDriverError
from boto.s3.connection import S3Connection
from boto.s3.key import Key

app = Flask(__name__)
app.config['S3_ACCESS_KEY'] = os.environ.get("S3_ACCESS_KEY")
app.config['S3_SECRET_KEY'] = os.environ.get("S3_SECRET_KEY")
app.config['S3_BUCKET'] = os.environ.get("S3_BUCKET")
app.config['DBHOST'] = os.environ.get("RETHINKDB_HOST")
app.config['DBPORT'] = os.environ.get("RETHINKDB_PORT")
app.config['DBNAME'] = os.environ.get("RETHINKDB_NAME")

#=========================helper functions=====================================
def allowed_file(filename):
    return ('.' in filename) and (filename.rsplit('.', 1)[1] in \
        set(['pdf', 'PDF']))

def make_id(): #returns unique str for new document's url
    return base64.urlsafe_b64encode(uuid.uuid4().bytes).strip("=")

def upload_to_S3(flask_file, unique_id):
    '''
    Uploads files to Amazon S3. 

    param flask_file: a file obj from flask.request.files['file']
    param unique_id: a url safe uuid from make_id()
    '''
    
    conn = S3Connection(app.config['S3_ACCESS_KEY'],
                        app.config['S3_SECRET_KEY'])
    bucket = conn.get_bucket(app.config['S3_BUCKET'])
    k = Key(bucket)
    k.key = unique_id + '.pdf'
    k.set_contents_from_string(flask_file.read())

def get_doc_from_S3(id):
    '''
    Returns binary pdf data from S3 as a string

    :param id: unique doc id as a string

    '''
    conn = S3Connection(app.config['S3_ACCESS_KEY'],
                        app.config['S3_SECRET_KEY'])
    bucket = conn.get_bucket(app.config['S3_BUCKET'])
    #no key validation because it should be there 
    #and validation requires an extra HEAD request
    key = bucket.get_key(id, validate=False)
    return key.get_contents_as_string()

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
                    upload_to_S3(file_to_upload, unique_id)
                except Exception:
                    abort(500, "Server couldn't upload to S3. Ugh.")
                else:
                    return jsonify({'docid': unique_id}) #docid is a str
            else:
                abort(500, "Server failed. Ugh.")
        else: #TODO? flash alert, but client side checks this anyway
            return redirect(url_for('index')) 
        
@app.route('/doc/<id>')
def get_pdf(id=None):
    if id is not None:
        #double check that doc is in database
        result = r.table("pdfs").get(id).run(g.db_conn)
            if result is not None:
                #return doc from S3
                try:
                    doc = get_doc_from_S3(id)
                except Exception:
                    abort(500, "Couldn't get doc from S3.")
                else:
                    fn = result["filename"]
                    response = make_response(doc) #doc is binary pdf string
                    response.headers['Content-Type'] = 'application/pdf'
                    response.headers['Content-Disposition'] = \
                        'inline; filename=%s.pdf' % fn
                    return response
            else:
                abort(500, "Couldn't find requested document.")
    return redirect(url_for('index'))

@app.route('/<id>')
def show_doc_or_collection(id=None):
    if id is not None:
        result = r.table("pdfs").get(id).run(g.db_conn)
        if result is not None: #doc in rethinkdb, render template with it
            return render_template('document.html', doc_id=id)
        else: #id might be for a collection, query db for collections with id
            result = r.table("collections").get(id).run(g.db_conn)
            if result is not None:
                db_cursor = r.table("join_ids")\
                    .get_all(id, index="collection_id")\
                    .eq_join("pdf_id", r.table("pdfs"))\
                    .without({"left": {"collection_id": True.
                                       "pdf_id": True}})\
                    .zip()\
                    .run(g.db_conn)
                #get list of dicts w/ docid, name, file size attrs
                doclist = [doc for doc in db_cursor]
                #TODO make attr names in template match those returned 
                #by db (changed attr names when switched to rethinkdb)
                return render_template('collection.html',
                    doclist={'doclist': doclist})
    else:
        redirect(url_for('index'))

@app.route('/collect', methods=["POST"])
def make_collection():
    doc_list = request.get_json()['docs']
    colid = make_id()
    try:
        response = r.table("collections").insert({"id": colid,
                                             "date_created": r.now()
                                             }).run(g.db_conn)
        if response['errors'] == 0:
            resp = r.table("join_ids").insert([{"pdf_id": doc,
                                                "collection_id": colid}
                                                for doc in doc_list])\
                                                .run(g.db_conn)
            return jsonify({'colid': colid})
        else:
            abort(500, "Server failed to make a collection")
    except Exception:
        abort(500, "Server failed to make a collection")

#==============================================================================
@app.errorhandler(404)
def page_not_found(error):
    return "Crap! I can't find that page @_@", 404

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8080)
