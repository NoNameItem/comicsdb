$(document).ready(function () {
  $('#mark-read-btn').click(function () {
    $.ajax({
        type : 'POST',
        url  : mark_read_url
      }
    ).done(function (response) {
      if (response.status === 'success') {
        successNotify("Congratulations!", "You have read " + response.issue_name + ".\n Time to read some more");
        $('#read-date-row').show();
        $('#read-mark').show();
        $('#read-date').text(response.date);
        $('#mark-read-btn').hide();
      } else {
        errorNotify("Oops! Can't mark issue as read", response.message);
      }
    })
  });

  $('#issue-title').select2({
    width          : '100%',
    dropdownParent : $('#issue-modal'),
    ajax           : {
      url            : title_list_url,
      data           : function (params) {
        return {
          name : params.term,
          page : params.page || 1
        };
      },
      delay          : 250,
      processResults : function (data) {
        return {
          results    : $.map(data.results, function (obj) {
            obj.text = obj.name_long;
            return obj;
          }),
          pagination : {more : !!data.next}
        };
      }
    }
  });

  $('#target-reading-list').select2({
    width          : '100%',
    dropdownParent : $('#add-to-list')
  });

  $('#add-to-list-btn').click(function () {
    $.ajax({
      url  : 'add-to-list',
      type : 'POST',
      data : {list_id : $('#target-reading-list').select2('data')[0].id}
    }).done(function (response) {
      console.debug(response);
      if (response.status === 'success') {
        successNotify("Congratulations!", "You have added " + response.issue_name + " to reading list "
          + response.list_name + ". Don't forget to actually read it)");
      } else {
        errorNotify("Oops! Can't add issue to reading list", response.message);
      }
    });
  });

  $('#issue-delete-btn').click(function () {
    swal({
      title      : "Delete confirmation",
      text       : "Are you realy want to delete this issue?",
      icon       : "error",
      buttons    : true,
      dangerMode : true,
    })
      .then((willDelete) => {
        if (willDelete) {
          swal("Ok, now we will delete this issue. Hope you glad!", {
            icon : "success",
          });
          setTimeout(function () {
            $('#delete-form').submit()
          }, 2000);
        } else {
          swal("Glad you changed your mind :)");
        }
      });
  });
});