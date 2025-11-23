scenario refund_bot {
    initial start;

    state start {
        intent greeting -> "您好，这里是退款助手，请问要退款的订单号是？" -> goto wait_order;
        intent ask_refund -> "好的，请提供需要退款的订单号。" -> goto wait_order;
        intent provide_order -> "已收到订单号：{user_input}。请问退款原因？" -> goto wait_reason;
        default -> "我可以帮您处理退款，请提供订单号。" -> goto wait_order;
    }

    state wait_order {
        intent provide_order -> "已收到订单号：{user_input}。请问退款原因？" -> goto wait_reason;
        default -> "请提供要退款的订单号（如 2024-001）。" -> goto wait_order;
    }

    state wait_reason {
        intent provide_reason -> "已记录原因：{user_input}。为您提交退款申请，请稍候..." -> goto done;
        intent cancel -> "已取消退款流程，如需帮助请再告知。" -> end;
        default -> "请简要说明退款原因，或输入取消。" -> goto wait_reason;
    }

    state done {
        default -> "退款申请已提交，您会收到后续通知。还有其他需要吗？" -> end;
    }
}
