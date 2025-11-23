scenario travel_bot {
    initial start;

    state start {
        intent greeting -> "您好，我能为您做什么？" -> goto routing;
        intent ask_order -> "好的，请提供您的订单号。" -> goto order;
        intent ask_flight -> "我可以帮您处理机票，请问目的地是哪里？" -> goto flight;
        default -> "我可以帮您查订单或预订机票，请问需要哪一项？" -> goto routing;
    }

    state routing {
        intent ask_order -> "好的，请提供您的订单号。" -> goto order;
        intent ask_flight -> "我可以帮您处理机票，请问目的地是哪里？" -> goto flight;
        default -> "我可以帮您查订单或预订机票，请问需要哪一项？" -> goto routing;
    }

    state order {
        intent provide_order -> "已收到订单号：{user_input}，正在为您查询..." -> end;
        default -> "请提供订单号（例如：2024-001）。" -> goto order;
    }

    state flight {
        intent provide_destination -> "目的地已记录：{user_input}。请问出行日期？" -> goto flight_date;
        default -> "请告诉我目的地城市。" -> goto flight;
    }

    state flight_date {
        intent provide_date -> "已收到日期 {user_input}，正在为您查询航班..." -> end;
        default -> "请提供日期，例如 2024-12-01。" -> goto flight_date;
    }
}
