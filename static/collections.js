$(document).ready(function(){
	var mockFile = {name: "filename.pdf", size: 12345};
	var doclist = {{doclist[0][0]}};
	console.log(doclist);
	Dropzone.options.myAwesomeDropzone = {
		init: function(){
			this.emit("addedfile", mockFile);
		}
	};
});