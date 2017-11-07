/**
 * Created by kecorbin on 10/6/17.
 */

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

