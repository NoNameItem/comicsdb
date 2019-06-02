let oldPos;

function deleteTitleHeading(el) {
  let $el = $(el);
  let $prev = $(el).prev();
  let $next = $(el).next();

  if ($prev.hasClass("not-draggable") && $next.hasClass("not-draggable")) {
    $prev.remove()
  }
}

function createTitleHeading(el) {
  let $el = $(el);
  let $prev = $(el).prev();
  let $next = $(el).next();

  if ($prev.hasClass("not-draggable")) {
    $prev.remove();
  }

  if ($prev.length === 0 || $el.attr("data-title") !== $prev.attr("data-title")) {
    let header = $(
      '<div class="col-12 m-1 not-draggable">\n' +
      '  <h3>' +
      $el.attr("data-title") +
      '  </h3>\n' +
      '</div>');
    header.insertBefore($el);
  }

  if ($next.hasClass("not-draggable") && $el.attr("data-title") === $next.text().trim()) {
    $next.remove();
  }
}

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
      deleteTitleHeading($('#issue-' + issue_id)[0]);
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
              $('#list-' + list_slug).remove();
            }
          }
        )
      } else {
        swal("Glad you changed your mind :)");
      }
    });
}

$(document).ready(function () {
  if (sortMode === "MANUAL") {
    var drake = dragula([document.querySelector('#draggable-container')], {
      moves : function (el, source, handle, sibling) {
        return $(el).hasClass("draggable");

      }
    });

    drake.on("drag", function (el, source) {
      deleteTitleHeading(el);
      oldPos = $(el).index(".draggable") + 1;
    });

    drake.on("drop", function (el, target, source, sibling) {
      createTitleHeading(el);

      if ($(sibling).hasClass("draggable")) {
        createTitleHeading(sibling);
      }

      let newPos = $(el).index(".draggable") + 1;

      console.log(oldPos);
      console.log(newPos);

      $.ajax({
        url  : 'reorder',
        type : 'POST',
        data : {
          issueID : $(el).attr("data-issue-id"),
          oldPos  : oldPos,
          newPos  : newPos
        }
      }).done(function (response) {
        if (response.status === 'success') {
          // successNotify("Congratulations!", "You have removed " + response.issue_name + " from reading list "
          //   + response.list_name + ".");
        } else {
          errorNotify("Oops! Can't  change reading list order", response.message);
        }
      });
    });

    drake.on("cancel", function (el, container, source) {
      createTitleHeading(el);
    });
  }
});