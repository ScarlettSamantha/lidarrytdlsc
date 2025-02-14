// socket.js
$(function () {
    // Connect to the Flask-SocketIO server.
    const socket = io();
  
    // Expose the socket globally so main.js can also use it.
    window.socket = socket;
  
    /**
     * LISTENS for socket calls
     */
    // Listen for cell updates.
    socket.on('update_cell', (data) => {
      const $row = $(`#row-${data.row_id}`);
      if ($row.length) {
        const $cell = $row.find(`td[data-column="${data.column}"]`);
        if ($cell.length) {
          $cell.text(data.new_value);
        }
      }
      window.addNotification(`Cell updated: Row ${data.row_id} — Column ${data.column} is now ${data.new_value}`, 'info');
    });
  
    // Listen for new rows.
    socket.on('new_row', (data) => {
      window.addRow(data.row);
      window.addNotification(`New row added: Row ${data.row.id}`, 'success');
    });
  
    // Listen for new columns.
    socket.on('add_column', (data) => {
      const { column, default_value } = data;
      const $headerRow = $('#table-header');
      const $th = $('<th></th>')
        .attr('scope', 'col')
        .attr('data-column', column.id)
        .addClass("px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider")
        .text(column.name);
      $headerRow.append($th);
  
      $('#table-body').find('tr').each(function () {
        const $td = $('<td></td>')
          .attr('data-column', column.id)
          .addClass("px-6 py-4 whitespace-nowrap text-sm text-gray-700")
          .text(default_value);
        $(this).append($td);
      });
  
      window.addNotification(`New column added: ${column.name}`, 'success');
    });

    socket.on('update_progress', (data) => {
        // Expecting data to contain a uuid and progress value.
        const { uuid, progress } = data;
        // Update the progress bar in the corresponding row.
        const $row = $(`#row-${uuid}`);
        if ($row.length) {
          // Assume the progress bar is the element with the class 'progress-bar'
          $row.find('.progress-bar').css('width', progress + '%');
        }
        window.addNotification(`Progress updated for row ${uuid}: ${progress}%`, 'info');
      });
  
    // Listen for column removals.
    socket.on('remove_column', (data) => {
      const colId = data.column_id;
      $('#table-header').find(`th[data-column="${colId}"]`).remove();
      $('#table-body').find('tr').each(function () {
        $(this).find(`td[data-column="${colId}"]`).remove();
      });
      window.addNotification(`Column removed: ${colId}`, 'error');
    });
  
    // New event: update the progress bar
    socket.on('update_progress', (data) => {
      // Expecting data to contain a uuid and progress value.
      const { uuid, progress } = data;
      window.updateProgress(uuid, progress);
      window.addNotification(`Progress updated for row ${uuid}: ${progress}%`, 'info');
    });

    socket.on('update_progress', (data) => {
      const { uuid, progress } = data;
      const $row = $(`#row-${uuid}`);
      if ($row.length) {
        $row.find('.progress-bar').css('width', progress + '%');
      }
      window.addNotification(`Progress updated for row ${uuid}: ${progress}%`, 'info');
    });
  
    socket.on('export_complete', (data) => {
      // data should look like: { ids: ["71ba21e1", "e2e89f24", ...] }
      const table = window.table; // or however you reference your DataTable
      console.log(table)
      data.ids.forEach((rowId) => {
        // Remove the row whose <tr> has id="row-<rowId>"
        // e.g. if rowId = "71ba21e1", the <tr> is <tr id="row-71ba21e1">...</tr>
        table.row(`#row-${rowId}`).remove();
      });
  
      // Redraw the table after removing rows
      table.draw(false);
    });

    // New listener for error notifications.
    socket.on('error_notification', (data) => {
      // Display the error notification.
      window.addNotification(data.message, 'error');
    });
    
    /**
     * Execute socket calls.
     */

    $(document).on('click', '#startTicketBtn', function() {
        const ticketId = $(this).data('ticket-id');
        // Emit the start_ticket event to the server.
        socket.emit('start_ticket', { ticket_id: ticketId });
      });

      // Example: Emitting start_ticket event when a button is clicked.
      $(document).on('click', '.start-ticket-btn', function() {
        const ticketId = $(this).data('ticket-id');
        socket.emit('start_ticket', { ticket_id: ticketId });
      });

      $("button#mass_export_selected").click(function(){
        let results = [];
        $("input.row-checkbox").each(function(){
          if ($(this).prop("checked")) {
            results.push($(this).attr("data-row-id"));
          }
        });
        socket.emit('export_selected_rows', { selected_id: results, action: 'export' });
      });
  });
  