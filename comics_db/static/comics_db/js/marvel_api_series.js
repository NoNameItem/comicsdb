let pagerContainer = $('#pager');
let pagerParams = {
  pagerInitialised : false,
  totalPages       : 0
};

let showIgnored = false;
let showMatched = false;

let controller = {
  loadData : function (filter) {
    let d = $.Deferred();
    let f = filter;
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

    $('.setup').map(function () {
      f[$(this).attr("name")] = $(this).is(':checked');
    });

    $.ajax({
      type : "GET",
      url  : "/api/marvel_api/series",
      data : f,
    })
      .done(function (response) {
          d.resolve({data : response.results, itemsCount : response.count});
        }
      );
    return d.promise();
  }
};

function toggleIgnore(series_id) {
  $.ajax({
    url  : "/api/marvel_api/series/" + series_id + "/toggle_ignore",
    type : 'POST',
  }).done(function (data, textStatus, jqXHR) {
    successNotify("Success", "Series visibility changed");
    $('#grid').jsGrid('loadData');
  }).fail(function (jqXHR, textStatus, errorThrown) {
    if (jqXHR.status === 404) {
      errorNotify("Series not found", "Please refresh page");
    } else {
      errorNotify("Error");
    }
  });
}

$(document).ready(function () {
  $setup = $('.setup');
  $setup.checkboxpicker();
  $setup.change(function () {
    $('#grid').jsGrid('loadData');
  });

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

    rowDoubleClick : function (obj) {
      let  url = "/marvel-api/series/" + obj.item.id;
      window.open(url,'_blank');
    },

    fields : [
      {
        type         : "control",
        width        : 25,
        itemTemplate : function (value, item) {
          return '<a href="#" onclick="toggleIgnore(' + item.id + ')" title="Toggle ignore" data-toggle="tooltip"\n' +
            '                     data-placement="bottom"><i class="fal ' + (item.ignore ? "fa-eye" : "fa-eye-slash") + '"></i></a>';
        }
      },
      {
        name  : "id",
        type  : "number",
        title : "ID",
        align : "center",
        width : 40
      },
      {
        name  : "title",
        type  : "text",
        title : "Title"
      },
      {
        name       : "series_type",
        type       : "select",
        items      : TYPE_LOV,
        valueField : "id",
        textField  : "name",
        title      : "Type",
        align      : "center",
        width      : 40
      },
      {
        name  : "start_year",
        type  : "number",
        title : "Start year",
        align : "center",
        width : 40
      },
      {
        name  : "end_year",
        type  : "number",
        title : "End year",
        align : "center",
        width : 40
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
});
