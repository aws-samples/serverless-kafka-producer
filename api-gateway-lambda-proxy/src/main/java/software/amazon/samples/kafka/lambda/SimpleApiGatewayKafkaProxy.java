// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
package software.amazon.samples.kafka.lambda;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyRequestEvent;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyResponseEvent;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.RecordMetadata;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import software.amazon.lambda.powertools.logging.Logging;
import software.amazon.lambda.powertools.tracing.Tracing;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.Future;

import static software.amazon.lambda.powertools.utilities.jmespath.Base64Function.decode;

public class SimpleApiGatewayKafkaProxy implements RequestHandler<APIGatewayProxyRequestEvent, APIGatewayProxyResponseEvent> {

    public static final String TOPIC_NAME = "messages";

    private static final Logger log = LogManager.getLogger(SimpleApiGatewayKafkaProxy.class);
    public KafkaProducerPropertiesFactory kafkaProducerProperties = new KafkaProducerPropertiesFactoryImpl();
    private KafkaProducer<String, String> producer;

    @Override
    @Tracing
    @Logging(logEvent = true)
    public APIGatewayProxyResponseEvent handleRequest(APIGatewayProxyRequestEvent input, Context context) {
        APIGatewayProxyResponseEvent response = createEmptyResponse();
        try {

            String message = getMessageBody(input);

            KafkaProducer<String, String> producer = createProducer();

            ProducerRecord<String, String> record = new ProducerRecord<String, String>(TOPIC_NAME, context.getAwsRequestId(), message);

            Future<RecordMetadata> send = producer.send(record);
            producer.flush();

            RecordMetadata metadata = send.get();
            log.info(String.format("Send message was send to partition %s", metadata.partition()));

            log.info(String.format("Message was send to partition %s", metadata.partition()));

            return response.withStatusCode(200).withBody("Message successfully pushed to kafka");
        } catch (Exception e) {
            log.error(e.getMessage(), e);
            return response.withBody(e.getMessage()).withStatusCode(500);
        }
    }

    @Tracing
    private KafkaProducer<String, String> createProducer() {
        if (producer == null) {
            log.info("Connecting to kafka cluster");
            producer = new KafkaProducer<String, String>(kafkaProducerProperties.getProducerProperties());
        }
        return producer;
    }


    private String getMessageBody(APIGatewayProxyRequestEvent input) {
        String body = input.getBody();

        if (input.getIsBase64Encoded()) {
            body = decode(body);
        }
        return body;
    }

    private APIGatewayProxyResponseEvent createEmptyResponse() {
        Map<String, String> headers = new HashMap<>();
        headers.put("Content-Type", "application/json");
        headers.put("X-Custom-Header", "application/json");
        APIGatewayProxyResponseEvent response = new APIGatewayProxyResponseEvent().withHeaders(headers);
        return response;
    }





}
