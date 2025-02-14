$(document).ready(function() {
  // Toggle user dropdown menu
  $('#user-menu-button').on('click', function () {
    $('#user-dropdown').toggleClass('hidden');
  });

  // Toggle notification menu
  $('div#notification-menu').on('click', function () {
    $('#notification-menu').toggleClass('hidden');
  });

  // Initialize DataTables with 100 records per page and Select extension
  window.table = $('#data-table').DataTable({
    pageLength: 100,            // Show 100 records by default
    select: {
      style: 'multi'            // Enable multi-row selection
    },
    initComplete: function () {
      // Style the page length select options
      $('.dataTables_length option').addClass(
        'bg-gray-500 text-white rounded px-3 py-2 appearance-none focus:outline-none focus:ring-2 focus:ring-gray-600'
      );

      // For each column, populate its filter dropdown with unique values.
      // Here we assume the <select> is in the header.
      this.api().columns().every(function () {
        var column = this;
        // Find the corresponding filter select in the filter row (skipping the first column which is for checkboxes)
        var headerCell = $(column.header());
        var select = headerCell.closest('thead').find('tr#filter-row th')
                        .eq(headerCell.index())
                        .find('select');
        if (select.length) {
          // Populate the select with distinct sorted values from the column
          column.data().unique().sort().each(function (d) {
            // Optionally, you might want to strip HTML tags if present
            if (d && select.find('option[value="'+d+'"]').length === 0) {
              select.append('<option value="'+d+'">'+d+'</option>');
            }
          });
          // When the user changes the filter, update the search for that column.
          select.on('change', function () {
            var val = $.fn.dataTable.util.escapeRegex($(this).val());
            column
              .search(val ? '^' + val + '$' : '', true, false)
              .draw();
          });
        }
      });
    }
  });

  // "Select All" checkbox logic
  $('#select-all').on('click', function(e) {
    e.preventDefault();
    var checked = $(this).prop('checked');
    // Update all checkboxes in the table (this will update only those in the DOM/visible page)
    $('#data-table').find('input[type="checkbox"]').prop('checked', checked);
  });
});
