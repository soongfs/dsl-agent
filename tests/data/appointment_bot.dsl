scenario appointment_bot {
    initial start;

    state start {
        intent greeting -> "您好，这里是预约助手，请问要预约什么服务？" -> goto service;
        default -> "请告诉我您要预约的服务类型（如医生、理发、维修）。" -> goto service;
    }

    state service {
        intent doctor -> "好的，为您预约医生，请提供日期。" -> goto date;
        intent haircut -> "好的，为您预约理发，请提供日期。" -> goto date;
        intent repair -> "好的，为您预约维修，请提供日期。" -> goto date;
        default -> "请说明要预约的服务：医生、理发或维修。" -> goto service;
    }

    state date {
        intent provide_date -> "收到日期：{user_input}，请确认是否提交预约。" -> goto confirm;
        default -> "请提供日期，例如 2024-12-01。" -> goto date;
    }

    state confirm {
        intent confirm -> "已提交预约，我们将尽快联系您确认。" -> end;
        intent reject -> "已取消预约，若需帮助请再联系。" -> end;
        default -> "请回复确认或取消。" -> goto confirm;
    }
}
