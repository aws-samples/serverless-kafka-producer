// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
package software.amazon.samples.kafka.lambda;

import java.util.Map;
import java.util.Properties;

public class KafkaProducerPropertiesFactoryImpl implements KafkaProducerPropertiesFactory {

    private Properties kafkaProducerProperties;

    public KafkaProducerPropertiesFactoryImpl() {

    }

    private String getBootstrapServer() {
        return System.getenv("bootstrap_server");
    }

    @Override
    public Properties getProducerProperties() {
        if (kafkaProducerProperties != null)
            return kafkaProducerProperties;

        String serializer = org.apache.kafka.common.serialization.StringSerializer.class.getCanonicalName();
        String callbackHandler = software.amazon.msk.auth.iam.IAMClientCallbackHandler.class.getCanonicalName();
        String loginModule = software.amazon.msk.auth.iam.IAMLoginModule.class.getCanonicalName();

        Map<String, String> configuration = Map.of(
                "key.serializer", serializer,
                "value.serializer", serializer,
                "bootstrap.servers", getBootstrapServer(),
                "security.protocol", "SASL_SSL",
                "sasl.mechanism", "AWS_MSK_IAM",
                "sasl.jaas.config", loginModule+ " required;",
                "sasl.client.callback.handler.class", callbackHandler,
                "connections.max.idle.ms", "60",
                "reconnect.backoff.ms", "1000"
        );

        kafkaProducerProperties = new Properties();

        for (Map.Entry<String, String> configEntry : configuration.entrySet()) {
            kafkaProducerProperties.put(configEntry.getKey(), configEntry.getValue());
        }



        return kafkaProducerProperties;
    }

}
