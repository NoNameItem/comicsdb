$(document).ready(function () {
    $('#log-table').DataTable({
      serverSide : true,
      ajax       : {
        url : '/api/parser-run',
        dataSrc : ''
      },
      columns: [
        {data: 'parser'},
        {data: 'status'}
      ]
    });
  }
);