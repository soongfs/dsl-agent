scenario faq_bot {
    initial start;

    state start {
        intent greeting -> "您好，这里是常见问题助手，请直接提问。" -> goto faq;
        default -> "我可以回答配送、退款政策、营业时间等问题，请问您的问题是？" -> goto faq;
    }

    state faq {
        intent shipping -> "标准配送 3-5 天，您也可以选择加急配送。" -> end;
        intent refund_policy -> "支持 7 天无理由退货，请保留包装和凭证。" -> end;
        intent working_hours -> "客服工作时间：周一至周五 9:00-18:00。" -> end;
        default -> "暂时没有相关答案，请换个说法或联系客服。" -> end;
    }
}
