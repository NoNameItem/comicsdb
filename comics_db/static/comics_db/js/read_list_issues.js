function delete_from_list(issue_id) {
  $.ajax({
    url  : 'delete-issue',
    type : 'POST',
    data : {issue_id : issue_id}
  }).done(function (response) {
    console.log(response);
    if (response.status === 'success') {
      successNotify("Congratulations!", "You have removed " + response.issue_name + " from reading list "
        + response.list_name + ".");
      $('#issue-' + issue_id).remove();
      $('#progress-bar').css('width', response.read_total_ratio + '%');
      $('#progress-bar-text').text(response.read + '/' + response.total);
    } else {
      errorNotify("Oops! Can't remove issue from reading list", response.message);
    }
  });
}

function delete_list(list_slug, redirect) {
  swal({
    title      : "Delete confirmation",
    text       : "Are you really want to delete this reading list? This operation can not be undone.",
    icon       : "error",
    buttons    : true,
    dangerMode : true,
  })
    .then((willDelete) => {
      if (willDelete) {
        swal("Ok, now we will delete this reading list. Hope you glad!", {
          icon : "success",
        });
        $.ajax({
          url  : '/reading-list/' + list_slug + '/delete',
          type : 'POST'
        }).done(function () {
            if (redirect) {
              window.location.replace('/reading-lists');
            } else {
              $('#list-'+list_slug).remove();
            }
          }
        )
      } else {
        swal("Glad you changed your mind :)");
      }
    });
}