from main import socketio
import random

def increment_ticket_progress(ticket_id, rate, table_rows):
    """
    Increment the progress of the ticket (row) with the given UUID until it reaches 100.
    Each increment occurs after 'rate' seconds and increases progress by a random amount.
    """
    progress = 0
    while progress < 100:
        socketio.sleep(rate)
        # Increase progress by a random amount between 1 and 10.
        increment = random.randint(1, 10)
        progress += increment
        if progress > 100:
            progress = 100
        # Update the corresponding row's progress.
        for row in table_rows:
            if row['id'] == ticket_id:
                row['progress'] = progress
                break
        # Emit the progress update so the client can update the progress bar.
        socketio.emit('update_progress', {'uuid': ticket_id, 'progress': progress})
        print(f"Ticket {ticket_id}: progress is now {progress}%")
        
        # When progress reaches 100, send an error notification.
        if progress == 100:
            socketio.emit('error_notification', {
                'uuid': ticket_id,
                'message': f'Ticket {ticket_id} has reached 100% progress.'
            })
            print(f"Ticket {ticket_id} has reached 100% progress. Error notification sent.")


@socketio.on('start_ticket')
def handle_start_ticket(data):
    """
    Start updating the progress for a given ticket (row) identified by its UUID.
    Expected data:
        { "ticket_id": <uuid> }
    """
    ticket_id = data.get('ticket_id')
    if not ticket_id:
        print("No ticket_id provided.")
        return
    # Choose a random update interval (rate) between 0.5 and 2.0 seconds.
    rate = random.uniform(0.5, 2.0)
    print(f"Starting progress update for ticket {ticket_id} at an interval of {rate:.2f} seconds.")
    socketio.start_background_task(increment_ticket_progress, ticket_id, rate)