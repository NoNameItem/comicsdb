let csrftoken = Cookies.get('csrftoken'); // Получаем csrf-токен из куки

/**
 * @summary Проверяет, требует ли метод передачи csrf-токена
 * @param method - проверяемый метод
 * @returns {*|boolean} - Проверяемый метод не требует передачи csrf-токена
 */
function csrfSafeMethod(method) {
  // these HTTP methods do not require CSRF protection
  return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

/**
 * @summary Переопределяет стандартный шаблон уведомления и вызывает bootstrap-notify
 * @param options - см. документацию на bootstrap-notify
 * @param settings - см. документацию на bootstrap-notify
 */
function myNotify(options, settings) {
  settings.template = '<div data-notify="container" class="notify col-xs-11 col-sm-3 alert alert-{0}" role="alert">' +
    '<button type="button" aria-hidden="true" class="close" data-notify="dismiss">×</button>' +
    '<div class="row">' +
    '<div class="icon-container col-1"' +
    '<span data-notify="icon"></span> ' +
    '</div>' +
    '<div class="text-container col-11">' +
    '<span data-notify="title">{1}</span> ' +
    '<span data-notify="message">{2}</span>' +
    '</div>' +
    '</div>' +
    '<div class="progress" data-notify="progressbar">' +
    '<div class="progress-bar progress-bar-{0}" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" style="width: 0%;"></div>' +
    '</div>' +
    '<a href="{3}" target="{4}" data-notify="url"></a>' +
    '</div>';
  $.notify(options, settings);
}

/**
 * @summary Стандартная функция вывода ошибок. Использует myNotify
 * @param title - Заголовок сообщения об ошибке
 * @param message - Сообщение об ошибке
 */
function errorNotify(title, message) {
  myNotify(
    {
      title   : title,
      message : message,
      icon    : "fa fa-exclamation-triangle"
    },
    {
      type          : "danger",
      delay         : 0,
      newest_on_top : true,
      animate       : {
		    enter : 'animated fadeInDown',
		    exit  : 'animated fadeOutDown'},
    }
  );
}

// Добавляем в идентификацию ajax-запросов csrf-токен там, где это необходимо
$.ajaxSetup({
  beforeSend: function (xhr, settings) {
    if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
      xhr.setRequestHeader("X-CSRFToken", csrftoken);
    }
  }
});

