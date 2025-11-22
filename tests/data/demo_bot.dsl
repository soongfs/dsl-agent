scenario demo_bot {
    initial start;

    state start {
        intent greeting -> "Hello! What can I do for you?" -> goto routing;
        default -> "Sorry, I missed that. How can I help?" -> goto start;
    }

    state routing {
        intent ask_order -> "Sure, please provide your order number." -> goto order;
        intent ask_flight -> "I can help with flights. Where are you flying to?" -> goto flight;
        default -> "I can help with orders or flights. Which one?" -> goto routing;
    }

    state order {
        intent provide_order -> "Got it: {user_input}. Checking status..." -> end;
        default -> "Please give an order number (e.g., 2024-001)." -> goto order;
    }

    state flight {
        intent provide_destination -> "Destination noted: {user_input}. What date?" -> goto flight_date;
        default -> "Tell me your destination city." -> goto flight;
    }

    state flight_date {
        intent provide_date -> "Date {user_input} received. Booking now..." -> end;
        default -> "Please give a date like 2024-12-01." -> goto flight_date;
    }
}
