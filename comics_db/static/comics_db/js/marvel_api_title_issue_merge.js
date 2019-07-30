let pagerContainer = $('#pager');
let pagerParams = {
  pagerInitialised : false,
  totalPages       : 0
};
let run_detail_id;
let db_id;

const STATUS_COLORS = {
  SUCCESS : 'success',
  ERROR   : 'danger',
  RUNNING : 'info'
};

const STATUS_LOV = [
  {name : "", id : ""},
  {name : "Running", id : "RUNNING"},
  {name : "Success", id : "SUCCESS"},
  {name : "Error", id : "ERROR"},
];

const MERGE_RESULT_LOV = [
  {name : "", id : ""},
  {id : 'SUCCESS', name : 'Success'},
  {id : 'NOT_FOUND', name : 'Match not found'},
  {id : 'DUPLICATES', name : 'Multiple matches'},
  {id : 'MANUAL', name : 'Manually changed'},
];

const ORDER_MAP = {
  'MARVEL_API_TITLE_MERGE' : {
    api_name : "api_title__title",
    db_name  : "db_title__name",
  }
};

function set_api_series(db_title_id, api_series_id) {
  $.ajax({
    url         : '/api/title/'+db_title_id+'/set_api_series',
    type        : 'POST',
    contentType : 'application/json; charset=utf-8',
    data        : JSON.stringify({
      api_series_id: api_series_id,
      run_detail_id: run_detail_id
    })
  }).done(function (data, textStatus, jqXHR) {
    successNotify("Success","API series assigned");
    $('#grid').jsGrid('loadData');
  }).fail(function (jqXHR, textStatus, errorThrown) {
    if (jqXHR.status === 404) {
      errorNotify("Not found", "Please refresh page");
    } else {

    }
  });
}

function set_api_comics(db_issue_id, api_comic_id) {
  $.ajax({
    url         : '/api/issue/'+db_issue_id+'/set_api_comic',
    type        : 'POST',
    contentType : 'application/json; charset=utf-8',
    data        : JSON.stringify({
      api_comic_id: api_comic_id,
      run_detail_id: run_detail_id
    })
  }).done(function (data, textStatus, jqXHR) {
    successNotify("Success","API series assigned");
    $('#grid').jsGrid('loadData');
  }).fail(function (jqXHR, textStatus, errorThrown) {
    if (jqXHR.status === 404) {
      errorNotify("Not found", "Please refresh page");
    } else {

    }
  });
}

function setManual(){
  let api_id = $('#modal-set-manual').val();
  if (!api_id){
    errorNotify("API ID not set")
  } else {
    if (parser === "MARVEL_API_TITLE_MERGE") {
      set_api_series(db_id, api_id);
    }
    if (parser === "MARVEL_API_ISSUE_MERGE") {
      set_api_comics(db_id, api_id);
    }
  }
}

function showStep(obj) {
  // Get step data
  $.ajax({
    type : "GET",
    url  : obj.item.detail_url,
  })
    .done(function (response) {
      run_detail_id = response.id;
      db_id = response.db_id;
        // Set fields
        $("#modal-api").text(response.api_name || '');
        $("#modal-db").html('<a href="'+response.site_link+'" target="_blank">'+response.db_name+'</a>');
        $("#modal-status").text(response.status_name);
        if (response.created) {
          $("#modal-created").html('<i class="far fa-check-circle success fa-2x"></i>');
        } else {
          $("#modal-created").html('<i class="far fa-times-circle danger fa-2x"></i>');
        }

        $("#modal-data").text(response.data);
        $("#modal-start").val(moment(response.start).format("DD.MM.YYYY hh:mm:ss.SSS"));
        $("#modal-end").val(moment(response.end).format("DD.MM.YYYY hh:mm:ss.SSS"));

        if (response.status === 'ERROR') {
          $('#modal-error-block').show();
          $('#modal-error').text(response.error);
          $('#modal-error-detail').text(response.error_detail);
        } else {
          $('#modal-error-block').hide();
        }

        if (parser === 'MARVEL_API_ISSUE_MERGE'){
          $('#modal-api-series-link').text(response.api_series_name).attr('href', response.api_series_link);

        }

        // Change modal coloring
        let color = STATUS_COLORS[response.status];
        $('#modal-header').removeClass("bg-success bg-danger bg-info").addClass("bg-" + color);
        $('#modal-status').removeClass("success danger info").addClass(color);
        $("#modal-content").removeClass("border-success border-danger border-info").addClass("border-" + color);
        $("#modal-content h4").removeClass("border-bottom-success border-bottom-danger border-bottom-info").addClass("border-bottom-" + color);
        $("#modal-footer").removeClass("border-top-success border-top-danger border-top-info").addClass("border-top-" + color);
        $("#modal-close-btn").removeClass("btn-outline-success btn-outline-danger btn-outline-info").addClass("btn-outline-" + color);

        // Possible matches
        if (response.merge_result === 'DUPLICATES') {
          $('#possible-matches').html(response.possible_matches);
          $('#possible-matches-outer').show();
        } else {
          $('#possible-matches-outer').hide();
        }
        // Open modal
        $('#run-detail-modal').modal()
      }
    );


}

let controller = {
  loadData : function (filter) {
    console.log(filter);
    let d = $.Deferred();
    let f = {};
    if (filter.sortParams) {
      f.ordering = filter.sortParams.map(function (filter) {
        let name = ORDER_MAP[parser][filter.f] || filter.f;
        return filter.o === "asc" ? name : "-" + name;
      }).join(",");
    }
    if (filter.pageIndex) {
      f.page = filter.pageIndex;
      f.page_size = filter.pageSize;
    }
    if (filter.start) {
      f.start_date = filter.start;
    }
    f.api_name = filter.api_name;
    f.db_name = filter.db_name;
    f.status = filter.status_name;
    f.merge_result = filter.merge_result;
    f.created = filter.created;
    f.error = filter.error;
    $.ajax({
      type : "GET",
      url  : details_url,
      data : f,
    })
      .done(function (response) {
          d.resolve({data : response.results, itemsCount : response.count});
        }
      );
    return d.promise();
  }
};

$(document).ready(function () {
  $('#grid').jsGrid({
    width  : "100%",
    height : "auto",

    sorting     : true,
    paging      : true,
    pageLoading : true,
    filtering   : true,
    pagerFormat : "",
    pageSize    : 20,

    controller : controller,
    autoload   : true,

    rowDoubleClick : showStep,

    fields : [
      {
        type         : "control",
        width        : 50,
        itemTemplate : function (value, item) {
          return '';
        }
      },
      {
        name         : "db_name",
        title        : "DB",
        type         : "text",
        align        : "left",
        width        : 250,
        cellRenderer : function (value, item) {
          return '<td><a href="' + item.site_link + '" target="_blank">' + value + '</a></td>';
        }
      },
      {
        name  : "api_name",
        title : "API",
        type  : "text",
        align : "left",
        width : 250
      },
      {
        name         : "status_name",
        type         : "select",
        title        : "Status",
        items        : STATUS_LOV,
        valueField   : "id",
        textField    : "name",
        width        : 120,
        cellRenderer : function (value, item) {
          return $('<td class="bg-' + STATUS_COLORS[item.status] + ' bg-lighten-4">').text(value)
        }
      },
      {
        name       : "merge_result",
        type       : "select",
        title      : "Merge result",
        items      : MERGE_RESULT_LOV,
        valueField : "id",
        textField  : "name",
        width      : 120,
        // cellRenderer : function (value, item) {
        //   return $('<td class="bg-' + STATUS_COLORS[item.status] + ' bg-lighten-4">').text(value)
        // }
      },
      {
        name      : "start",
        type      : "date",
        width     : 120,
        title     : "Start",
        filtering : false
      },
      {
        name      : "end",
        type      : "date",
        width     : 120,
        title     : "End",
        filtering : false
      },
      {
        name    : "error",
        type    : "text",
        title   : "Error",
        width   : 200,
        sorting : false
      },
    ],

    onDataLoaded        : getSetPager(pagerContainer, pagerParams),
    loadIndicationDelay : 0,
    loadIndicator       : {
      show : function () {
        var block_ele = $('#run-detail-card');

        // Block Element
        block_ele.block({
          message    : '<div class="ft-refresh-cw icon-spin font-medium-2"></div>',
          //timeout: 2000, //unblock after 2 seconds
          overlayCSS : {
            backgroundColor : '#FFF',
            cursor          : 'wait',
          },
          css        : {
            border          : 0,
            padding         : 0,
            backgroundColor : 'none'
          }
        });
      },
      hide : function () {
        $('#run-detail-card').unblock();
      }

    }
  });
});