// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
package software.amazon.samples.kafka.lambda;

import software.amazon.lambda.powertools.tracing.Tracing;

import java.util.Properties;

public interface KafkaProducerPropertiesFactory {

    @Tracing
    Properties getProducerProperties();
}
