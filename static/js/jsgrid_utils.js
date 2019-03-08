// Кастомные поля jsGrid

// Дата
let MyDateField = function(config) {
    jsGrid.Field.call(this, config);
};

MyDateField.prototype = new jsGrid.Field({

    css: "date-field",            // redefine general property 'css'
    align: "center",              // redefine general property 'align'


    sorter: function(date1, date2) {
        return new Date(date1) - new Date(date2);
    },

    itemTemplate: function(value) {
        return new Date(value).toLocaleString();
    },

    insertTemplate: function(value) {
        return this._insertPicker = $("<input>").datetimepicker({format: 'DD.MM.YYYY' });
    },

    filterTemplate: function(value) {
      if (this.filtering)
        return this._filterPicker = $("<input>").datetimepicker({format: 'DD.MM.YYYY' });
      else
        return "";
    },

    editTemplate: function(value) {
        this._editPicker = $("<input>").datetimepicker({format: 'DD.MM.YYYY'});
        this._editPicker.data("DateTimePicker").date(new Date(value));
        return this._editPicker
    },

    insertValue: function() {
      var insertValue = this._insertPicker.data('DateTimePicker').date();
			if (typeof insertValue !== 'undefined' && insertValue !== null) {
				return insertValue.format("YYYY-MM-DD");
			} else {
				return null;
			}
    },

    filterValue: function() {
      var filterValue = this._filterPicker.data('DateTimePicker').date();
			if (typeof filterValue !== 'undefined' && filterValue !== null) {
				return filterValue.format("YYYY-MM-DD");
			} else {
				return null;
			}
    },

    editValue: function() {
      var editValue = this._editPicker.data('DateTimePicker').date();
			if (typeof editValue !== 'undefined' && editValue !== null) {
				return editValue.format("YYYY-MM-DD");
			} else {
				return null;
			}
    }
});

jsGrid.fields.date = MyDateField;

// Вспомогательные функции для работы с jsGrid

/**
 * @summary Выводит стандартные алерты с сообщениями об ошибке при вводе данных
 * @requires common.js
 * @param args - объект, содержащий массив ошибок ввода данных (см. документацию jsGrid invalidNotify)
 */
function gridErrorNotify(args) {
  $.notifyClose();
  $.map(
    args.errors,
    function (error) {
      errorNotify('Ошибка ввода данных', error.message);
    }
  );
}

/**
 * @summary Превращение скучного стандартного тултипа в нескучный красивый
 * @param arg - объект с полем row, содержащим jquery-элемент строки, в которой надо украсить тултипы
 */
function gridErrorTooltip(arg) {
    arg.row.find('.jsgrid-invalid').map(function(e) {
      $(this).attr("data-toggle", "tooltip");
      $(this).attr("data-placement", "bottom");
      $(this).tooltip({container : 'body', trigger : 'hover'});
    })
  }


/**
 * @summary Общая функция для обработки ошибок ввода данных
 * @description Парсинг ответа от DRF с учетом вложенности + генерация алертов с ошибками + заполнение тултипов у полей.
   Для корректной работы с полями, относящимся к вложенным моделям (модели, на которые используется ссылка)
   следует в настройках грида указывать editcss и insertcss по аналогии с фильтрами по вложенным моделям в джанго.
   Например, если модели Employee есть Поле-внешний ключ Department у которого есть поле name, и это поле выводится в грид
   то editcss и insertcss должны называться department__name
 * @param row - jquery-элемент строки, в которой надо инициализировать тултипы
 * @param prefix - аккумулирующий параметр, в котором собирается вложенность моделей друг в друга
 * @param name - имя текущего поля
 * @param obj - массив с ожибками в данном поле
 */
function processFieldError(row, prefix, name, obj) {
  if ($.isArray(obj)){
    let field_error_title = "";
    row.find('.jsgrid-cell.' + prefix + name).addClass('jsgrid-invalid');
    for (let i in obj) {
      errorNotify('Ошибка ввода данных', obj[i]);
      field_error_title += obj[i];
    }
    row.find('.jsgrid-cell.' + prefix + name).prop("title", field_error_title);
  } else {
    for (i in obj) {
      processFieldError(row, prefix + name + '__', i, obj[i]);
    }
  }
}

// Верхнеуровневая функция, запускающая обработку ошибок для заданного ответа сервера.
// Предназначена для использования в обработчике ошибок при вставке/редактировании
/**
 * @summary Верхнеуровневая функция, запускающая обработку ошибок для заданного ответа сервера.
  Предназначена для использования в обработчике ошибок при вставке/редактировании
 * @param response - ответ от веб-сервера, содержащий ошибке в формате DRF
 * @param row - jquery-селектор редактируемой строки
 */
function responseGridErrorNotify(response, row) {
  row.find(".jsgrid-cell").removeClass("jsgrid-invalid").removeProp("title");
  $.notifyClose();
  for (let i in response.responseJSON) {
    processFieldError(row, "", i, response.responseJSON[i]);
  }
}

// Генераторы функций для грида

/**
 * @summary Генератор функций для инициализации пагинатора после обновления данных
 * @generator
 * @param pagerContainer - селектор контейнера пагинатора
 * @param pagerParams - объект, в котором хранится текущее состояние пагинатора. Должен иметь 2 поля
 *  pagerInitialised - флаг того, что пагинатор инициализован
 *  totalPages - общее число страниц в результирующем наборе данных
 * @returns {Function} - функция с сигнатурой onDataLoaded, которая перерисовывает пагинатор после подгрузки данных
 */
function getSetPager(pagerContainer, pagerParams) {
  return function(obj) {
    let itemsCount = obj.data.itemsCount;
    let pageSize = obj.grid.pageSize;
    let currentPage = obj.grid.pageIndex;
    let pageCount = (itemsCount - itemsCount % pageSize) / pageSize + (itemsCount % pageSize === 0 ? 0 : 1);


    function initPager(container, p_pageCount, p_currentPage) {
      console.log("initPager");
      if (p_pageCount !== 0) {
        container.twbsPagination({
          totalPages: p_pageCount,
          startPage: p_currentPage,
          hideOnlyOnePage: false,
          visiblePages: 10,
          paginationClass: "pagination justify-content-end",
          initiateStartPageClick: false,
          first: '<<',
          prev: '<',
          next: '>',
          last: '>>',
          // handler
          onPageClick: function (e, page) {
            obj.grid.openPage(page);
          }
        });
      }
    }

    if (!pagerParams.pagerInitialised) {
      initPager(pagerContainer, pageCount, currentPage);
      pagerParams.pagerInitialised = true;
    } else {
      if (pageCount !== 0 && (currentPage !== pagerContainer.twbsPagination("getCurrentPage")) || (pagerParams.totalPages !== pageCount)) {
        pagerContainer.twbsPagination("destroy");
        initPager(pagerContainer, pageCount, currentPage);
      }
    }
    pagerParams.totalPages = pageCount;
  }
}

/**
 * @summary Генерирует функции для переключения строки в режим редактирования
 * @generator
 * @param grid_selector - селектор элемента грида
 * @returns {Function} - Функция, принимающая объект вида
 *   {
       item - данные строки грида
       itemIndex - индекс строки грида на странице
       event - событие, породившее вызов функции
     }
 * и переключающая строку item в режим редактирования
 */
function getRowEdit(grid_selector){
  return function(obj){
    $(grid_selector).jsGrid("editItem", obj.item);
  }
}

/**
 * @summary Генерирует функции для выделения строк
 * @generator
 * @param grid_selector - селектор элемента грида
 * @param callback - функция, обрабатывающая выделение строки. Должна принимать объект obj (см. ниже)
 * @returns {Function} - Функция, принимающая объект obj вида
 *   {
       item - данные строки грида
       itemIndex - индекс строки грида на странице
       event - событие, породившее вызов функции
     }
 * визуально выделяющая выбранную строку и запускающая функцию обработки выделения
 */
function getRowSelect(grid_selector, callback){
  let $callback = callback || function (obj) {};
  return function (obj) {
    let $row = $(grid_selector).jsGrid("rowByItem", obj.item);
    $(grid_selector).find("tr.selected").removeClass("selected");
    $row.addClass("selected");
    $callback(obj);
  }
}

$.extend(jsGrid.Grid.prototype, {

    _sortParams: [],

    _createHeaderRow: function () {
        if ($.isFunction(this.headerRowRenderer))
            return $(this.renderTemplate(this.headerRowRenderer, this));
        var $result = $("<tr>").addClass(this.headerRowClass);
        this._eachField(function (field, index) {
            var $th = this._prepareCell("<th>", field, "headercss", this.headerCellClass)
                .append(this.renderTemplate(field.headerTemplate, field))
                .appendTo($result);
            if (this.sorting && field.sorting) {
                $th.addClass(this.sortableClass)
                    .on("click", $.proxy(function (e) {
                        $.extend(this,{_sortEvent:e})
                        this.sort(index);
                    }, this));
            }
        });
        return $result;
    },

    sort: function (field, order) {
        if ($.isPlainObject(field)) {
            order = field.order;
            field = field.field;
        }
        if(!(this._sortEvent.shiftKey)){
           this._clearSortingCss();
           this._sortParams=[];
        }
        this._setSortingParams(field, order);
        this._setSortingCss();
        return this._loadStrategy.sort();
    },
    _setSortingCss: function () {
        var fieldIndex = this._visibleFieldIndex(this._sortField);
        this._headerRow.find("th").eq(fieldIndex).removeClass(this.sortAscClass).removeClass(this.sortDescClass)
            .addClass(this._sortOrder === "asc" ? this.sortAscClass : this.sortDescClass);
    },
    _setSortingParams: function (field, order) {
        field = this._normalizeField(field);
        order = order || ((this._sortField === field) ? this._reversedSortOrder(this._sortOrder) : "asc");
        this._sortParams = $.grep(this._sortParams, function (e) {
            return e.field.name != field.name;
        });
        this._sortParams.push({field: field, order: order});
        this._sortField = field;
        this._sortOrder = order;
    },
    _resetSorting: function () {
        this._sortField = null;
        this._sortOrder = "asc";
        this._sortParams = [];
        this._clearSortingCss();
    },
    _sortingParams: function () {
        if (this.sorting && this._sortParams.length > 0) {
            return {
                sortParams: this._sortParams.map(function (v) {
                    return {f: v.field.name, o: v.order};
                })
            };
        }
        return {};
    },

    getSorting: function () {
        return this._sortParams.map(function (v) {
            return {field: v.field, order: v.order};
        });
    }
});
