// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
package software.amazon.samples.kafka.lambda;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyRequestEvent;
import com.amazonaws.services.lambda.runtime.tests.EventLoader;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.junit.After;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;
import org.junit.runner.RunWith;
import org.mockito.Mock;
import org.mockito.junit.MockitoJUnitRunner;

import java.time.Duration;
import java.util.Arrays;
import java.util.Properties;

import static org.junit.Assert.assertEquals;
import static org.mockito.Mockito.when;


@RunWith(MockitoJUnitRunner.class)
public class SimpleApiGatewayKafkaProxyTest {

    private KafkaLocalServer server;

    @Rule
    public TemporaryFolder folder = new TemporaryFolder();

    @Before
    public void setup() throws Exception {
        server = new KafkaLocalServer(folder.newFolder(), 2181);
        server.start();
    }

    @After
    public void teardown() throws Exception {
        server.stop();
    }

    @Mock
    private Context contextMock;

    @Mock
    private KafkaProducerPropertiesFactory kafkaProducerPropertiesFactoryMock;

    @Test
    public void handleRequest() {

        when(contextMock.getAwsRequestId()).thenReturn("1");
        when(kafkaProducerPropertiesFactoryMock.getProducerProperties()).thenReturn(producerProps());

        SimpleApiGatewayKafkaProxy simpleApiGatewayKafkaProxy= new SimpleApiGatewayKafkaProxy();
        simpleApiGatewayKafkaProxy.kafkaProducerProperties = kafkaProducerPropertiesFactoryMock;



        APIGatewayProxyRequestEvent event = EventLoader.loadApiGatewayRestEvent("src/test/resources/test_event.json");

        simpleApiGatewayKafkaProxy.handleRequest(event, contextMock);
        Properties consumerProps = consumerProperties();


        KafkaConsumer<String, String> consumer = new KafkaConsumer<>(consumerProps);
        consumer.subscribe(Arrays.asList(SimpleApiGatewayKafkaProxy.TOPIC_NAME));
        ConsumerRecords<String, String> record = consumer.poll(Duration.ofSeconds(5));

        assertEquals (record.count() ,1);
    }

    private Properties consumerProperties() {

        Properties props = new Properties();
        props.put("bootstrap.servers", server.getZookeeperConnectionString());
        props.put("group.id", "group1");
        props.put("key.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");
        props.put("value.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");
        props.put("auto.offset.reset", "earliest");
        return props;
    }

    private Properties producerProps() {
        Properties props = new Properties();
        props.put("bootstrap.servers", server.getZookeeperConnectionString());
        props.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer");
        props.put("value.serializer", "org.apache.kafka.common.serialization.StringSerializer");
        return props;
    }


}