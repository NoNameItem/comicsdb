let pagerContainer = $('#pager');
let pagerParams = {
  pagerInitialised : false,
  totalPages       : 0
};

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

const ORDER_MAP = {
  parser_code : "parser",
  status_name : "status",
  start       : "start",
  end         : "end"
};

function showStep(obj) {
  console.log(obj);
  // Get step data
  $.ajax({
    type : "GET",
    url  : obj.item.detail_url,
  })
    .done(function (response) {
        console.log(response);
        // Set fields
        $("#modal-action").text(response.action_name);
        $("#modal-entity").text(response.entity_type_name);
        $("#modal-status").text(response.status_name);

        $("#modal-data").text(response.data);
        $("#modal-start").val(moment(response.start).format("DD.MM.YYYY hh:mm:ss.SSS"));
        $("#modal-end").val(moment(response.end).format("DD.MM.YYYY hh:mm:ss.SSS"));

        if (response.status === 'ERROR'){
          $('#modal-error-block').show();
          $('#modal-error').text(response.error);
          $('#modal-error-detail').text(response.error_detail);
        } else {
          $('#modal-error-block').hide();
        }


        // Change modal coloring
        let color = STATUS_COLORS[response.status];
        $('#modal-header').removeClass("bg-success bg-danger bg-info").addClass("bg-" + color);
        $('#modal-status').removeClass("success danger info").addClass(color);
        $("#modal-content").removeClass("border-success border-danger border-info").addClass("border-" + color);
        $("#modal-content h4").removeClass("border-bottom-success border-bottom-danger border-bottom-info").addClass("border-bottom-" + color);
        $("#modal-footer").removeClass("border-top-success border-top-danger border-top-info").addClass("border-top-" + color);
        $("#modal-close-btn").removeClass("btn-outline-success btn-outline-danger btn-outline-info").addClass("btn-outline-" + color);

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
    f.file_key = filter.step_name;
    f.status = filter.status_name;
    f.created = filter.created
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

    rowClick : showStep,

    fields : [
      {
        type         : "control",
        width        : 50,
        itemTemplate : function (value, item) {
          return '';
        }
      },
      {
        name  : "step_name",
        type  : "text",
        title : "Step",
        width : 400,
        align : "left"
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