function addTask(){
  let d = {};
  $('.add-task-input').map(function(){
    if ($(this).attr("type") === "checkbox"){
      d[$(this).attr("name")] = $(this).is(':checked') ? $(this).val() : null;
    } else {
      d[$(this).attr("name")] = $(this).val();
    }
  });
  $.ajax({
      type : "POST",
      url  : "/api/parser_schedule",
      data : d
    }
  ).done(function(response){
    console.log(response);
    if (response.status === 'error'){
      errorNotify("Can't add schedule", response.message);
    } else {
      successNotify("Success", response.message);
    }
  });
}

const PARSER_LOV = [
  {name : "", id : ""},
  {name : "Base parser", id : "BASE"},
  {name : "Cloud files parser", id : "CLOUD_FILES"},
  {name : "Marvel API parser", id : "MARVEL_API"}
];

$(document).ready(function (){
  $('#parser-code').change(function () {
    $('.parser-run-form-group').hide();
    $('.parser-run-form-group-' + $('#parser-code').val()).show();
  });
  $('#schedule-type').change(function () {
    $('.row.schedule-parameters').hide();
    $('.row.schedule-parameters.' + $('#schedule-type').val()).show();
  });
  $('#add-task-btn').click(addTask);


});