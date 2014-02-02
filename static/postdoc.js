$(document).ready(function(){

	var dropped_docs = {'docs': []};

	Dropzone.options.myAwesomeDropzone = {
		init: function() {
			this.on("success", function(file, responseText) {

				var docid = responseText["docid"];
				$('.dz-success:last').attr('id', docid);
				var url = 'http://127.0.0.1:5000/'.concat(docid);

				var view = $('<button/>', {
					type: "button",
					text: "View pdf",
				});
				var button = $('<button/>', {
					type: "button",
					class: "clippy",
				});

				$('<input/>', {
					type: "text",
					readonly: "readonly",
					value: url,
				}).appendTo('.dz-success:last');
				button.appendTo('.dz-success:last');
				view.appendTo('.dz-success:last');
				button.clippy({
					clippy_path: '/static/clippy.swf',
					text: url
				});
				view.click(function(){
					window.open(url);
				});
				$('.dz-success:last input:text').click(function(e){
					$(this).focus().select();
				});

				dropped_docs['docs'].push(docid);
				
				if (dropped_docs['docs'].length===2){
					
					var button2 = $('<button/>', {
						type: "button",
						text: "Make a Collection",
						id: "collector",
					});
					button2.appendTo($('#container'));
					$('#collector').click(function(){
						$.ajax({
							type: "POST",
							data: JSON.stringify(dropped_docs),
							contentType: 'application/json',
							url: '/collect',
							dataType: 'json',
							success: function(data, textStatus, jqXHR){

								var colid = data['colid'];
								var colurl = 'http://127.0.0.1:5000/c/'.concat(colid);

								var div = $('<div/>', {
									id: "collected",
								});
								var colinput = $('<input/>', {
									type: "text",
									readonly: "readonly",
									value: colurl,
								});
								
								var colclip = $('<button/>', {
									type: "button",
									class: "clippy",
								});
								var colview = $('<button/>', {
									type: "button",
									text: "View collection",
								});
								colinput.appendTo(div);
								colclip.appendTo(div);
								colview.appendTo(div);
								$('#collector').remove();
								div.appendTo($('#container'));
								colclip.clippy({
									clippy_path: '/static/clippy.swf',
									text: colurl,
								});
								colview.click(function(){
									window.open(colurl);
								});
								$('#collected input:text').click(function(e){
									$(this).focus().select();
								});
							},
						});
					});
				};

			});
		}
	};
});