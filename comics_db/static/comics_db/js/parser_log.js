let pagerContainer = $('#pager');
let pagerParams = {
  pagerInitialised : false,
  totalPages       : 0
};

const STATUS_COLORS = {
  SUCCESS           : 'bg-success',
  ENDED_WITH_ERRORS : 'bg-warning',
  API_THROTTLE      : 'bg-warning',
  CRITICAL_ERROR    : 'bg-danger',
  INVALID_PARSER    : 'bg-danger',
  RUNNING           : 'bg-info',
  COLLECTING        : 'bg-info'
};

const PARSER_LOV = [
  {name : "", id : ""},
  {name : "Base parser", id : "BASE"},
  {name : "Cloud files parser", id : "CLOUD_FILES"},
  {name : "Marvel API parser", id : "MARVEL_API"}
];

const STATUS_LOV = [
  {name : "", id : ""},
  {name : "Running", id : "RUNNING"},
  {name : "Collecting data", id : "COLLECTING"},
  {name : "Successfully ended", id : "SUCCESS"},
  {name : "Ended with errors", id : "ENDED_WITH_ERRORS"},
  {name : "Critical Error", id : "CRITICAL_ERROR"},
  {name : "Invalid parser implementation", id : "INVALID_PARSER"}
];

const ORDER_MAP = {
  parser_code : "parser",
  status_name : "status",
  start       : "start",
  end         : "end"
};

let controller = {
  loadData : function (filter) {
    console.log(filter);
    let d = $.Deferred();
    let f = {};
    if (filter.sortParams) {

      f.ordering = filter.sortParams.map(function (filter) {
        return filter.o === "asc" ? ORDER_MAP[filter.f] : "-" + ORDER_MAP[filter.f];
      }).join(",");
    }
    if (filter.pageIndex) {
      f.page = filter.pageIndex;
      f.page_size = filter.pageSize;
    }
    if (filter.start) {
      f.start_date = filter.start;
    }
    f.parser = filter.parser_code;
    f.status = filter.status_name;
    f.start_date = filter.start;
    f.end_date = filter.end;
    f.error = filter.error;
    $.ajax({
      type : "GET",
      url  : "/api/parser_run",
      data : f,
    })
      .done(function (response) {
          d.resolve({data : response.results, itemsCount : response.count});
        }
      );
    return d.promise();
  }
};


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

  rowClick : function (obj) {
    window.location.href = obj.item.page;
  },

  fields : [
    {
      type         : "control",
      width        : 25,
      itemTemplate : function (value, item) {
        return "<a href='" + item.page + "'><i class='fa fa-list'></i></a>";
      }
    },
    {
      name       : "parser_code",
      type       : "select",
      items      : PARSER_LOV,
      title      : "Parser",
      valueField : "id",
      textField  : "name",
      align      : "left"
    },
    {
      name         : "status_name",
      type         : "select",
      title        : "Status",
      items        : STATUS_LOV,
      valueField   : "id",
      textField    : "name",
      cellRenderer : function (value, item) {
        return $('<td class="' + STATUS_COLORS[item.status_code] + ' bg-lighten-4">').text(value)
      }
    },
    {
      name  : "start",
      type  : "date",
      title : "Start"
    },
    {
      name  : "end",
      type  : "date",
      title : "End"
    },
    {
      name    : "error",
      type    : "text",
      title   : "Error",
      sorting : false
    },
  ],

  onDataLoaded        : getSetPager(pagerContainer, pagerParams),
  loadIndicationDelay : 0,
  loadIndicator       : {
    show : function () {
      var block_ele = $('#grid-card');

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
      $('#grid-card').unblock();
    }

  }
});

function startParser() {
  let d = {};
  d.parser_code = $('#parser-code').val();
  $('.parser-run-input').map(function () {
    if ($(this).attr("type") === "checkbox") {
      d[$(this).attr("name")] = $(this).is(':checked') ? $(this).val() : null;
    } else {
      d[$(this).attr("name")] = $(this).val();
    }
  });
  // console.log(d);
  $.ajax({
      type : "POST",
      url  : "/run_parser",
      data : d
    }
  ).done(function (response) {
    console.log(response);
    if (response.status === 'error') {
      errorNotify("Can't start parser", response.message);
    } else {
      successNotify("Parser started", response.message);
      $('#start-parser-modal').modal('hide');
      $('#grid').jsGrid('clearFilter');
    }
  });
}

$(document).ready(function () {
  $('#parser-code').change(function () {
    $('.parser-run-form-group').hide();
    $('.parser-run-form-group-' + $('#parser-code').val()).show();
  });
  $('#start-parser-btn').click(startParser);

});