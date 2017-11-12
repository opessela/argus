/**
 * Created by kecorbin on 10/6/17.
 */
function shouldHideSidebar() {
    if ($(window).width() < 992) {
        $('#appSidebar').addClass('sidebar--hidden');
    }
}
function doNav(url) {
    shouldHideSidebar();
    document.location.href = url;
}

$(document).ready(function() {

    // Wire the header sidebar toggle button
    $('#appHeader .toggle-menu').click(function () {
        $('#appSidebar').toggleClass('sidebar--hidden');
    });
    // Wire the sidebar drawer open/close toggles
    $('#appSidebar .sidebar__drawer > a').click(function() {
        $(this).parent().toggleClass('sidebar__drawer--opened');
    });

    // Wire the sidebar selected item
    $('#appSidebar .sidebar__item > a').click(function() {
        $('#appSidebar .sidebar__item').removeClass('sidebar__item--selected');
        $(this).parent().addClass('sidebar__item--selected');
    });
}
)
var events = $('#events-table').DataTable( {
    "ajax": {
            "type" : "GET",
            "url" : "/api/events",
            "dataSrc": function ( json ) {
                return json;
            }
            },

    "columns": [
                    { "data": "action" },
                    { "data": "id" },
                    { "data": "timestamp"},
                    { "data": "epg"},
                    { "data": "node"},
                    { "data": "port" },
                    { "data": "vlan" },
                    { "data": "ucsm"},
                    { "data": "id",
                        "render": function (data, type, row, meta) {
                            event_id = row.id
                       return ' <button onclick="deleteEvent(event_id)" class="btn btn--icon btn--small btn--negative"><span class="icon-trash"></span></button>'
                        }
                    }
                ]
    }
);


function deleteEvent(id) {
    $.ajax({
        url: '/api/events/' + id,
        method: 'DELETE'
    })
    events.ajax.reload();
}


// auto refresh the datatable
setInterval( function () {
    events.ajax.reload();
}, 10000 );

