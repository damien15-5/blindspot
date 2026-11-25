# Social drafts · unpublished

## X

My classifier recognized a museum guitar until the lights dimmed. BlindSpot saved that failure in Pinecone on a live @flydotio Sprite and tried low light first on a second guitar. This one passed. See the replay https://blindspot-demo-b6wzw.sprites.app

## Bluesky

JPEG compression fooled my classifier on a second museum guitar. My BlindSpot agent first tried low light because its live @flydotio Sprite recalled another guitar’s failure from Pinecone. This guitar kept its label until JPEG level 3. Explore the replay https://blindspot-demo-b6wzw.sprites.app

## LinkedIn

I built BlindSpot for @flydotio Hacksgiving to answer a question about inventory photos. When a classifier recognizes an object, which change in lighting or image quality makes it lose the label?

Eleven of twelve museum photos already missed their labels in the original shot. One guitar passed, so BlindSpot tested it under different camera conditions. Low light caused an error. The live Sprite saved that failure through the Pinecone connector.

When I gave BlindSpot a different guitar, Pinecone recalled the failure and the agent moved low light ahead of its usual blur test. The second guitar passed both. At the strongest JPEG compression, the classifier confidently picked the wrong label.

[Explore the public sample replay](https://blindspot-demo-b6wzw.sprites.app) · [Read the code](https://github.com/damien15-5/blindspot)
