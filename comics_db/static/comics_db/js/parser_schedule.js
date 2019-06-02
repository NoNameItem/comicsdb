let pagerContainer = $('#pager');
let pagerParams = {
  pagerInitialised : false,
  totalPages       : 0
};

function addTask() {
  let d = {};
  $('.add-task-input').map(function () {
    if ($(this).attr("type") === "checkbox") {
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
  ).done(function (response) {
    console.log(response);
    if (response.status === 'error') {
      errorNotify("Can't add schedule", response.message);
    } else {
      successNotify("Success", response.message);
    }
  });
}

const PARSER_LOV = [
  {name : "", id : ""},
  {name : "Cloud files parser", id : "CLOUD_FILES"},
  {name : "Marvel API parser", id : "MARVEL_API"}
];

const SCHEDULE_TYPE_LOV = [
  {name : "", id : ""},
  {name : "Crontab", id : "Crontab"},
  {name : "Interval", id : "Interval"}
];

let controller = {
  loadData : function (filter) {
    let d = $.Deferred();
    let f = {};
    if (filter.sortParams) {
      f.ordering = filter.sortParams.map(function (filter) {
        let name = ORDER_MAP[filter.f] || filter.f;
        return filter.o === "asc" ? name : "-" + name;
      }).join(",");
    }
    if (filter.pageIndex) {
      f.page = filter.pageIndex;
      f.page_size = filter.pageSize;
    }

    $.ajax({
      type : "GET",
      url  : schedule_url,
      data : f,
    })
      .done(function (response) {
        console.log(response);
          d.resolve(response);
        }
      );
    return d.promise();
  },

  updateItem : function(item){
    $.ajax({
      url         : schedule_url + '/' + item.id,
      type        : 'PUT',
      contentType : 'application/json; charset=utf-8',
      data        : JSON.stringify(item)
    }).done(function (data, textStatus, jqXHR) {
      successNotify("Changes saved");
    }).fail(function (jqXHR, textStatus, errorThrown) {
      if (jqXHR.status === 404) {
        errorNotify("Task not found", "Please, refresh page");
      } else {
      }
    });
  },

  deleteItem : function (item) {
    $.ajax({
      url         : schedule_url + '/' + item.id,
      type        : 'DELETE',
    }).done(function (data, textStatus, jqXHR) {
      successNotify("Deleted from schedule");
    }).fail(function (jqXHR, textStatus, errorThrown) {
      if (jqXHR.status === 404) {
        errorNotify("Task not found", "Please, refresh page");
      } else {
      }
    });
  }
};

$(document).ready(function () {
  $('#parser-code').change(function () {
    $('.parser-run-form-group').hide();
    $('.parser-run-form-group-' + $('#parser-code').val()).show();
  });
  $('#schedule-type').change(function () {
    $('.row.schedule-parameters').hide();
    $('.row.schedule-parameters.' + $('#schedule-type').val()).show();
  });
  $('#add-task-btn').click(addTask);

  $('#grid').jsGrid({
    width  : "100%",
    height : "auto",

    sorting     : true,
    paging      : false,
    pageLoading : false,
    filtering   : false,
    editing     : true,
    pagerFormat : "",

    controller : controller,
    autoload   : true,

    // rowClick : showStep,

    fields : [
      {
        type         : "control",
        width        : 100,
      },
      {
        name  : "enabled",
        title : "Enabled",
        type  : "checkbox",
        align : "center",
        width : 70,
        editing : true,
        sorting : true,
      },
      {
        name  : "name",
        title : "Name",
        type  : "text",
        align : "left",
        width : 200,
        editing : true,
        sorting : true,
      },
      {
        name       : "parser",
        title      : "Parser",
        type       : "select",
        items      : PARSER_LOV,
        valueField : "id",
        textField  : "name",
        align      : "left",
        width      : 100,
        editing : false,
        sorting : true,

      },
      {
        name  : "init_args",
        title : "Arguments",
        type  : "text",
        align : "left",
        width : 200,
        editing : false,
        sorting : false,
      },
      {
        name       : "schedule_type",
        title      : "Schedule type",
        type       : "select",
        items      : SCHEDULE_TYPE_LOV,
        valueField : "id",
        textField  : "name",
        align      : "left",
        width : 120,
        editing : false,
        sorting : true,
      },
      {
        name  : "interval__every",
        title : "Every",
        type  : "number",
        align : "left",
        width : 70,
        editing : false,
        sorting : false,
      },
      {
        name  : "interval__period",
        title : "Period",
        type  : "text",
        align : "left",
        width : 100,
        editing : false,
        sorting : false,
      },
      {
        name  : "crontab__minute",
        title : "Minute",
        type  : "text",
        align : "left",
        width : 70,
        editing : false,
        sorting : false,
      },
      {
        name  : "crontab__hour",
        title : "Hour",
        type  : "text",
        align : "left",
        width : 70,
        editing : false,
        sorting : false,
      },
      {
        name  : "crontab__day_of_week",
        title : "Day of week",
        type  : "text",
        align : "left",
        width : 100,
        editing : false,
        sorting : false,
      },
      {
        name  : "crontab__day_of_month",
        title : "Day of month",
        type  : "text",
        align : "left",
        width : 120,
        editing : false,
        sorting : false,
      },
      {
        name  : "crontab__month_of_year",
        title : "Month of year",
        type  : "text",
        align : "left",
        width : 120,
        editing : false,
        sorting : false,
      },
      {
        name  : "total_run_count",
        title : "Run count",
        type  : "number",
        align : "left",
        width : 100,
        editing : false,
        sorting : false,
      },
      {
        name  : "last_run_at",
        title : "Last run",
        type  : "text",
        align : "left",
        width : 100,
        editing : false,
        sorting : true,
      },
      {
        name  : "description",
        title : "Description",
        type  : "text",
        align : "left",
        width : 250,
        editing : true,
        sorting : false,
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