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
        return filter.o === "asc" ? filter.f : "-" + filter.f;
      }).join(",");
    }
    if (filter.pageIndex) {
      f.page = filter.pageIndex;
      f.page_size = filter.pageSize;
    }
    if (filter.start) {
      f.start_date = filter.start;
    }

    if (series_id){
      f.series_id = series_id;
    }

    $('.setup').map(function () {
      f[$(this).attr("name")] = $(this).is(':checked');
    });

    $.ajax({
      type : "GET",
      url  : "/api/marvel_api/comics",
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
      let url = "/marvel-api/comics/" + obj.item.id;
      window.open(url,'_blank');
    },

    fields : [
      {
        type         : "control",
        width        : 10,
        itemTemplate : function (value, item) {
          return '';
        }
      },
      {
        name  : "id",
        type  : "number",
        title : "ID",
        align : "center",
        width : 25
      },
      {
        name  : "title",
        type  : "text",
        title : "Title",
        width : 70
      },
      {
        name  : "issue_number",
        type  : "number",
        title : "Issue number",
        align : "center",
        width : 30
      },
      {
        name  : "page_count",
        type  : "number",
        title : "Page count",
        align : "center",
        width : 30
      },
      {
        name  : "description",
        type  : "text",
        title : "Description"
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
