$('#title-delete-btn').click(function () {
  swal({
    title      : "Delete confirmation",
    text       : "Are you really want to delete this title? All issues will be deleted too.",
    icon       : "error",
    buttons    : true,
    dangerMode : true,
  })
    .then((willDelete) => {
      if (willDelete) {
        swal("Ok, now we will delete this title and all its issues. Hope you glad!", {
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

$('#move-issues-btn').click(function () {
  swal({
    title      : "Move confirmation",
    text       : "Are you really want to move all issues and delete title? This action can't be undone.",
    icon       : "error",
    buttons    : true,
    dangerMode : true,
  })
    .then((willMove) => {
      if (willMove) {
        swal("Ok, now we will move all issues and delete this title and all its issues. Hope you know what you are doing!", {
          icon : "success",
        });
        setTimeout(function () {
          $('#move-form').submit()
        }, 2000);
      }
    });
});

$(document).ready(function () {
  $('#target-title').select2({
    width          : '100%',
    dropdownParent : $('#move-issue-modal'),
    ajax           : {
      url            : titles_url,
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
      data : {
        list_id     : $('#target-reading-list').select2('data')[0].id,
        number_from : $('#from-number').val(),
        number_to   : $('#to-number').val()
      }
    }).done(function (response) {
      console.debug(response);
      if (response.status === 'success') {
        successNotify("Congratulations!", "You have added " + response.issue_count + " issue(s) to reading list "
          + response.list_name + ". Don't forget to actually read it)");
      } else {
        errorNotify("Oops! Can't add issues to reading list", response.message);
      }
    });
  });
});