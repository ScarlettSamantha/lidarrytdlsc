// main.js
$(function () {
  /**
   * Add a notification to the persistent notifications menu.
   *
   * @param {string} message - The notification message.
   * @param {string} [type='info'] - The type ('info', 'success', 'error').
   */
  function addNotification(message, type = 'info') {
    const $notificationList = $('#notification-list');
    const typeColors = {
      'info': 'border-blue-500',
      'success': 'border-green-500',
      'error': 'border-red-500'
    };
    const borderColor = typeColors[type] || typeColors['info'];

    // Create a new notification list item.
    const $item = $(`
      <li class="p-4 border-l-4 ${borderColor} hover:bg-gray-300 transition-colors duration-200">
        <div class="flex justify-between items-center">
          <span class="text-gray-400">${message}</span>
          <button class="text-gray-500 hover:text-gray-700 focus:outline-none remove-notification">&times;</button>
        </div>
      </li>
    `);

    // Remove the notification if the close button is clicked.
    $item.find('.remove-notification').on('click', function () {
      $item.remove();
      updateNotificationCount();
    });

    // Prepend the new notification so it appears at the top.
    $notificationList.prepend($item);
    updateNotificationCount();
  }

  /**
   * Update the notification count badge.
   */
  function updateNotificationCount() {
    const count = $('#notification-list').children().length;
    const $countBadge = $('#notification-count');
    $countBadge.text(count);
    $countBadge.toggleClass('hidden', count === 0);
  }

  /**
   * Add a new row to the table.
   *
   * @param {object} row - The row data.
   */
  function addRow(row) {
    // Create a new table row with the row id.
    let $row = $(`<tr id="row-${row.id}" class="hover:bg-gray-400"></tr>`);

    // First cell: display the row's id.
    $row.append(`<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 break-all">${row.id}</td>`);

    // For each column (assuming a global "columns" array), add a cell.
    columns.forEach((col) => {
      $row.append(`<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700" data-column="${col.id}">${row[col.id] || ''}</td>`);
    });

    // Append the new row to the table body.
    $('#table-body').append($row);
  }

  /**
   * Update and animate the progress bar in a specific row.
   *
   * @param {string} uuid - The row's unique identifier.
   * @param {number} progress - The new progress value (0 to 100).
   */
  function updateProgress(uuid, progress) {
    const $row = $(`#row-${uuid}`);
    if ($row.length) {
      // Look for the progress bar element (using a class for easier targeting)
      const $progressBar = $row.find('.progress-bar');
      if ($progressBar.length) {
        // Animate the width change
        $progressBar.animate({ width: progress + '%' }, 500);
      }
    }
  }

  // UI event handlers

  // Toggle the notifications menu when the bell icon is clicked.
  $('#notification-button').on('click', function () {
    $('#notification-menu').toggleClass('hidden');
  });

  // Clear all notifications.
  $('#clear-notifications').on('click', function () {
    $('#notification-list').empty();
    updateNotificationCount();
  });

  // Button to add a new column.
  $('#add-column-btn').on('click', () => {
    // The "socket" object is defined in socket.js (ensure main.js loads first)
    window.socket.emit('add_column_request', {});
  });

  // Button to remove the last column.
  $('#remove-column-btn').on('click', () => {
    window.socket.emit('remove_column_request', {});
  });

  // Handle user input form submission.
  $('#user-input-form').on('submit', function (e) {
    e.preventDefault();
    const rowId = $('#row-id-input').val().trim();
    const column = $('#column-input').val().trim();
    const newValue = $('#new-value-input').val().trim();
    if (rowId && column && newValue) {
      window.socket.emit('user_input', {
        row_id: rowId,
        column: column,
        new_value: newValue
      });
      // Clear the form after submission.
      $(this).trigger('reset');
    }
  });

  // Initialize the notification count.
  updateNotificationCount();

  // Expose these functions so that socket.js can use them.
  window.addNotification = addNotification;
  window.addRow = addRow;
  window.updateProgress = updateProgress;
});
