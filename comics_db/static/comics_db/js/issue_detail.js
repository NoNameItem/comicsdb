$(document).ready(function () {
  $('#mark-read-btn').click(function () {
    $.ajax({
        type: 'POST',
        url: 'mark-read'
      }
    ).done(function (response) {
      console.log(response);
      if (response.status === 'success') {
        successNotify("Congratulations!", "You read " + response.issue_name + ".\n Time to read some more");
        $('#read-date-row').show();
        $('#read-date').text(response.date);
        $('#mark-read-btn').hide();
      } else {
        errorNotify("Oops! Can't mark issue as read", response.message);
      }
    })
  });
});