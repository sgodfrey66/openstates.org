import React from "react";

export default class LegislatorImage extends React.Component {
  constructor(props) {
    super(props);

    if (props.id && props.image) {
      this.state = {
        url: "https://data.openstates.org/images/small/" + props.id,
      };
    } else {
      this.state = {
        url: null,
      };
    }
  }

  render() {
    const component = this;
    const modifier = this.props.size === "medium" ? "mr1" : "thumbnail--small";
    if (!this.state.url) {
      return (
        <div className={"thumbnail thumbnail--placeholder " + modifier}></div>
      );
    } else {
      return (
        <img
          className={"thumbnail " + modifier}
          src={this.state.url}
          alt="headshot for legislator"
          onError={() => component.setState({ url: null })}
        />
      );
    }
  }
}
